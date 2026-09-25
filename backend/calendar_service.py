import datetime
import json
import os
import re
from typing import Any, Dict, Optional, Tuple
import requests

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")
SCOPES = "https://www.googleapis.com/auth/calendar.events"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/api/calendar/callback")


def get_oauth_credentials() -> Tuple[Optional[str], Optional[str]]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret or client_id.strip() == "" or client_secret.strip() == "":
        return None, None
    return client_id.strip(), client_secret.strip()


def get_auth_url() -> Tuple[Optional[str], Optional[str]]:
    client_id, client_secret = get_oauth_credentials()
    if not client_id or not client_secret:
        return None, "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing or not configured in backend/.env"

    scope_encoded = requests.utils.quote(SCOPES)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        f"&scope={scope_encoded}"
        "&access_type=offline"
        "&prompt=consent"
    )
    return auth_url, None


def handle_oauth_callback(code: str) -> Tuple[bool, str]:
    client_id, client_secret = get_oauth_credentials()
    if not client_id or not client_secret:
        return False, "Missing Google OAuth credentials"

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    try:
        resp = requests.post(token_url, data=data, timeout=10)
        if resp.status_code != 200:
            return False, f"Failed to exchange code: {resp.text}"

        token_data = resp.json()
        token_data["created_at"] = datetime.datetime.now(datetime.timezone.utc).timestamp()

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

        return True, "Successfully authenticated"
    except Exception as e:
        return False, f"OAuth token exchange error: {str(e)}"


def load_valid_token() -> Tuple[Optional[str], Optional[str]]:
    if not os.path.exists(TOKEN_FILE):
        return None, "Not authenticated with Google Calendar"

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token_data = json.load(f)
    except Exception:
        return None, "Failed to read local token file"

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    created_at = token_data.get("created_at", 0)

    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if access_token and (now - created_at < expires_in - 60):
        return access_token, None

    # Refresh token if expired
    if refresh_token:
        client_id, client_secret = get_oauth_credentials()
        if not client_id or not client_secret:
            return None, "Missing Google OAuth credentials for token refresh"

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            resp = requests.post(token_url, data=data, timeout=10)
            if resp.status_code == 200:
                new_token_data = resp.json()
                token_data["access_token"] = new_token_data.get("access_token", access_token)
                token_data["expires_in"] = new_token_data.get("expires_in", expires_in)
                token_data["created_at"] = now
                if "refresh_token" in new_token_data:
                    token_data["refresh_token"] = new_token_data["refresh_token"]

                with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                    json.dump(token_data, f, indent=2)

                return token_data["access_token"], None
        except Exception:
            pass

    return None, "Google Calendar session expired. Please re-authenticate."


def parse_time_slot_to_iso(slot_str: str, base_date: datetime.date) -> Tuple[Optional[str], Optional[str]]:
    """Converts a time_slot string like '9:00 AM - 10:00 AM' into start and end ISO 8601 strings."""
    parts = re.split(r"[-–]", slot_str)
    if len(parts) != 2:
        return None, None

    def parse_time_part(t_str: str) -> Optional[datetime.datetime]:
        t_str = t_str.strip()
        m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)?$", t_str, re.IGNORECASE)
        if not m:
            return None
        h = int(m.group(1))
        mn = int(m.group(2))
        p = m.group(3).upper() if m.group(3) else None
        if p == "PM" and h < 12:
            h += 12
        elif p == "AM" and h == 12:
            h = 0
        dt = datetime.datetime(base_date.year, base_date.month, base_date.day, h, mn)
        return dt.astimezone()

    start_dt = parse_time_part(parts[0])
    end_dt = parse_time_part(parts[1])

    if not start_dt or not end_dt:
        return None, None

    if end_dt <= start_dt:
        end_dt += datetime.timedelta(days=1)

    return start_dt.isoformat(), end_dt.isoformat()


def export_schedule_to_calendar(schedule_items: list) -> Tuple[Dict[str, Any], int]:
    access_token, err = load_valid_token()
    if err or not access_token:
        auth_url, _ = get_auth_url()
        return {
            "error": err or "Authentication required",
            "authenticated": False,
            "auth_url": auth_url,
        }, 401

    if not isinstance(schedule_items, list) or len(schedule_items) == 0:
        return {"error": "No schedule items provided to export"}, 400

    today = datetime.date.today()
    created_events = []
    errors = []

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    for item in schedule_items:
        title = item.get("title", "Untitled Task")
        slot = item.get("time_slot", "")
        item_type = item.get("type", "task")
        notes = item.get("notes", "")

        start_iso, end_iso = parse_time_slot_to_iso(slot, today)
        if not start_iso or not end_iso:
            errors.append(f"Could not parse time slot for '{title}' ({slot})")
            continue

        desc_parts = [f"Category: {item_type}"]
        if notes:
            desc_parts.append(f"Notes: {notes}")
        description = "\n".join(desc_parts)

        event_payload = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_iso,
            },
            "end": {
                "dateTime": end_iso,
            },
        }

        cal_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        try:
            resp = requests.post(cal_url, headers=headers, json=event_payload, timeout=10)
            if resp.status_code in (200, 201):
                created_events.append(resp.json().get("id"))
            elif resp.status_code == 401:
                auth_url, _ = get_auth_url()
                return {
                    "error": "Authentication token expired. Please re-authenticate.",
                    "authenticated": False,
                    "auth_url": auth_url,
                }, 401
            else:
                errors.append(f"Failed to create event '{title}': {resp.status_code}")
        except Exception as ex:
            errors.append(f"Network error creating event '{title}': {str(ex)}")

    if not created_events and errors:
        return {"error": f"Failed to export events to Google Calendar. Details: {'; '.join(errors)}"}, 500

    return {
        "success": True,
        "events_created": len(created_events),
        "message": f"Successfully exported {len(created_events)} item(s) to Google Calendar.",
        "warnings": errors if errors else None,
    }, 200
