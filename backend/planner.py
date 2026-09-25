import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Load backend/.env before any os.getenv calls
load_dotenv()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_plan_request(
    data: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validates incoming JSON payload for schedule generation."""
    if not data or not isinstance(data, dict):
        return None, "Invalid request payload: must be a JSON object"

    tasks = data.get("tasks") or data.get("goals")
    working_hours = (
        data.get("working_hours")
        or data.get("available_working_hours")
        or data.get("available_hours")
    )

    if not tasks:
        return None, "Missing required field: 'tasks' or 'goals'"
    if isinstance(tasks, list) and len(tasks) == 0:
        return None, "'tasks' list cannot be empty"
    if not working_hours:
        return None, "Missing required field: 'working_hours' or 'available_working_hours'"

    return {
        "tasks": tasks,
        "working_hours": working_hours,
        "priorities": data.get("priorities", []),
        "deadlines": data.get("deadlines", []),
        "fixed_commitments": data.get("fixed_commitments", []),
    }, None


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _parse_minutes(t_str: str) -> int:
    """Convert a 12-hour time string like '9:00 AM' to minutes since midnight."""
    t_str = t_str.strip()
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)?$", t_str, re.IGNORECASE)
    if not m:
        return 0
    h, mn = int(m.group(1)), int(m.group(2))
    p = m.group(3).upper() if m.group(3) else None
    if p == "PM" and h < 12:
        h += 12
    elif p == "AM" and h == 12:
        h = 0
    return h * 60 + mn


def _parse_slot_range(slot: str) -> Tuple[int, int]:
    """Return (start_minutes, end_minutes) from a slot string like '9:00 AM - 1:00 PM'."""
    parts = re.split(r"[-\u2013]", slot)
    if len(parts) == 2:
        return _parse_minutes(parts[0]), _parse_minutes(parts[1])
    return 0, 0


def _minutes_to_str(m_val: int) -> str:
    """Convert minutes-since-midnight to a 12-hour AM/PM string."""
    h = m_val // 60
    mn = m_val % 60
    period = "PM" if h >= 12 else "AM"
    h12 = h % 12 or 12
    return f"{h12}:{mn:02d} {period}"


# ---------------------------------------------------------------------------
# Fixed commitment parser
# ---------------------------------------------------------------------------

def _parse_fixed_commitments(raw: List) -> List[Dict]:
    """
    Parse strings like 'Lunch (1:00 PM - 2:00 PM)' into
    [{"title": "Lunch", "time_slot": "1:00 PM - 2:00 PM"}, ...]
    """
    result = []
    for fc in raw:
        if isinstance(fc, str):
            m = re.match(r"^(.*?)\s*\((.*?)\)$", fc.strip())
            if m:
                result.append({
                    "title": m.group(1).strip(),
                    "time_slot": m.group(2).strip(),
                })
    return result


# ---------------------------------------------------------------------------
# Schedule normalisation
# ---------------------------------------------------------------------------

def _normalise_schedule(
    schedule: List[Dict],
    parsed_fcs: List[Dict],
) -> List[Dict]:
    """
    1. Remove hallucinated break entries that duplicate fixed commitments.
    2. Ensure every fixed commitment is present with its exact title/time.
    3. Push any task that overlaps a fixed commitment to avoid the conflict.
    4. Sort chronologically.
    """
    fc_titles_lower = [fc["title"].lower() for fc in parsed_fcs]

    # Step 1 - drop duplicate breaks
    cleaned: List[Dict] = []
    for item in schedule:
        is_dup_break = item.get("type") == "break" and any(
            fc_t in item.get("title", "").lower() for fc_t in fc_titles_lower
        )
        if not is_dup_break:
            cleaned.append(item)

    # Step 2 - lock fixed commitments (update existing or append missing)
    for fc in parsed_fcs:
        fc_title = fc["title"]
        fc_slot = fc["time_slot"]
        found = False
        for item in cleaned:
            title_match = item.get("title", "").strip().lower() == fc_title.lower()
            partial_match = (
                fc_title.lower() in item.get("title", "").strip().lower()
                and item.get("type") == "fixed_commitment"
            )
            if title_match or partial_match:
                item["title"] = fc_title
                item["time_slot"] = fc_slot
                item["type"] = "fixed_commitment"
                found = True
                break
        if not found:
            cleaned.append({
                "time_slot": fc_slot,
                "title": fc_title,
                "type": "fixed_commitment",
                "priority": "high",
                "notes": "",
            })

    # Step 3 - resolve task overlaps with fixed commitments
    fc_ranges = [
        _parse_slot_range(fc["time_slot"])
        for fc in parsed_fcs
        if _parse_slot_range(fc["time_slot"]) != (0, 0)
    ]
    for item in cleaned:
        if item.get("type") != "task":
            continue
        s, e = _parse_slot_range(item.get("time_slot", ""))
        if s == 0 and e == 0:
            continue
        for fc_s, fc_e in fc_ranges:
            if max(s, fc_s) < min(e, fc_e):          # overlap detected
                if s >= fc_s and e <= fc_e:           # task fully inside fc
                    s = fc_e
                elif s < fc_s and e > fc_s:
                    if e <= fc_e:
                        e = fc_s
                    else:
                        s = fc_e
                if s < e:
                    item["time_slot"] = f"{_minutes_to_str(s)} - {_minutes_to_str(e)}"

    # Step 4 - chronological sort
    cleaned.sort(key=lambda x: _parse_slot_range(x.get("time_slot", ""))[0])
    return cleaned


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_day_plan(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Generate a daily schedule using the Gemini REST API.
    Returns (response_dict, http_status_code) matching the contract expected
    by app.py and the frontend.
    """
    # Reload .env in case Flask loaded before dotenv ran
    load_dotenv()

    # 1. Validate input
    validated, err = validate_plan_request(data)
    if err or validated is None:
        return {"error": err or "Invalid request input"}, 400

    # 2. Read and verify API key (never log it)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        return {"error": "GEMINI_API_KEY is missing or not configured in backend/.env"}, 500

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

    # 3. Build prompt
    prompt = (
        "You are an expert AI Day Planner. "
        "Return ONLY a single valid JSON object with no markdown or code fences.\n\n"
        "JSON schema:\n"
        "{\n"
        "  \"summary\": \"<short plan summary>\",\n"
        "  \"total_tasks_scheduled\": <integer>,\n"
        "  \"schedule\": [\n"
        "    {\n"
        "      \"time_slot\": \"<H:MM AM/PM - H:MM AM/PM>\",\n"
        "      \"title\": \"<title>\",\n"
        "      \"type\": \"<task|fixed_commitment|break>\",\n"
        "      \"priority\": \"<high|medium|low>\",\n"
        "      \"notes\": \"<brief note>\"\n"
        "    }\n"
        "  ],\n"
        "  \"unassigned_tasks\": [\"<task title if it could not fit>\"]\n"
        "}\n\n"
        f"Tasks / Goals: {json.dumps(validated['tasks'])}\n"
        f"Priorities: {json.dumps(validated['priorities'])}\n"
        f"Deadlines: {json.dumps(validated['deadlines'])}\n"
        f"Available Working Hours: {validated['working_hours']}\n"
        f"Fixed Commitments: {json.dumps(validated['fixed_commitments'])}\n\n"
        "RULES:\n"
        "1. Every Fixed Commitment is an IMMUTABLE HARD BLOCK. "
        "Include each with type='fixed_commitment' and its EXACT time_slot as given.\n"
        "2. No task or break may overlap any fixed commitment.\n"
        "3. Schedule everything within the available working hours.\n"
        "4. All time_slot strings MUST use 12-hour format with AM/PM "
        "(e.g. '9:00 AM - 10:30 AM').\n"
        "5. Place high-priority tasks in the best focus windows.\n"
        "6. Return ONLY the JSON object. No explanation, no markdown."
    )

    # 4. Call Gemini REST API - x-goog-api-key only, no OAuth, no Authorization header
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        # build_opener() creates a FRESH opener with no handlers from google-auth
        # or any other library that may have patched the global default opener.
        opener = urllib.request.build_opener()
        with opener.open(req) as resp:
            raw = resp.read().decode("utf-8")

    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        return {"error": f"Gemini API error {e.code}: {body_text}"}, 502
    except urllib.error.URLError as e:
        return {"error": f"Gemini network error: {str(e.reason)}"}, 502

    # 5. Parse API response envelope
    try:
        api_resp = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Gemini returned non-JSON envelope"}, 500

    candidates = api_resp.get("candidates", [])
    if not candidates:
        return {"error": "Gemini returned no candidates"}, 500

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts or not parts[0].get("text"):
        return {"error": "Gemini returned an empty response"}, 500

    response_text = parts[0]["text"].strip()

    # Strip markdown code fences if the model added them despite instructions
    if response_text.startswith("```"):
        response_text = re.sub(r"^```[a-zA-Z]*\n?", "", response_text)
        response_text = re.sub(r"\n?```$", "", response_text).strip()

    # 6. Parse model JSON output
    try:
        result_data = json.loads(response_text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse Gemini schedule output as JSON"}, 500

    # 7. Normalise / validate schedule
    parsed_fcs = _parse_fixed_commitments(validated.get("fixed_commitments", []))
    result_data["schedule"] = _normalise_schedule(
        result_data.get("schedule", []), parsed_fcs
    )

    return {"success": True, "plan": result_data}, 200
