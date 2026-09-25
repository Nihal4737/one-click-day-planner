import datetime
import os
import re
import requests
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


def format_notion_id(raw_id: str) -> str:
    """Format Notion 32-char hex string to standard 8-4-4-4-12 UUID format if needed."""
    clean = raw_id.replace("-", "").strip()
    if len(clean) == 32:
        return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"
    return raw_id.strip()


def get_notion_headers(api_key: str, version: Optional[str] = None) -> Dict[str, str]:
    """Build headers for Notion API requests."""
    notion_version = version or os.getenv("NOTION_VERSION", "2026-03-11").strip()
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    }


def locate_notion_target(
    api_key: str, page_id: str, version: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    Locates target database_id, data_source_id, and properties schema starting from NOTION_PAGE_ID.
    Returns (database_id, data_source_id, properties_schema, error_message).
    """
    if not api_key:
        return None, None, None, "NOTION_API_KEY is missing or not configured."
    if not page_id:
        return None, None, None, "NOTION_PAGE_ID is missing or not configured."

    headers = get_notion_headers(api_key, version)
    clean_id = format_notion_id(page_id)

    def _extract_from_db_object(db_data: dict) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
        db_id = db_data.get("id")
        data_sources = db_data.get("data_sources") or []
        if data_sources and isinstance(data_sources, list):
            ds_id = data_sources[0].get("id")
            if ds_id:
                ds_resp = requests.get(
                    f"https://api.notion.com/v1/data_sources/{ds_id}",
                    headers=headers,
                    timeout=10,
                )
                if ds_resp.status_code == 200:
                    ds_data = ds_resp.json()
                    return db_id, ds_id, ds_data.get("properties", {})
        props = db_data.get("properties")
        if props is not None:
            return db_id, None, props
        return db_id, None, {}

    # 1. Check if clean_id is directly a database ID
    db_url = f"https://api.notion.com/v1/databases/{clean_id}"
    try:
        resp = requests.get(db_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            db_id, ds_id, props = _extract_from_db_object(resp.json())
            return db_id, ds_id, props, None
    except Exception:
        pass

    # 2. Check if clean_id is a data_source ID directly
    ds_url = f"https://api.notion.com/v1/data_sources/{clean_id}"
    try:
        resp = requests.get(ds_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            ds_data = resp.json()
            props = ds_data.get("properties", {})
            db_id = (ds_data.get("parent") or {}).get("database_id", clean_id)
            return db_id, clean_id, props, None
    except Exception:
        pass

    # 3. Query page block children for a child_database
    children_url = f"https://api.notion.com/v1/blocks/{clean_id}/children?page_size=100"
    try:
        resp = requests.get(children_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            for block in results:
                block_type = block.get("type")
                if block_type == "child_database":
                    child_db_id = block.get("id")
                    child_db_resp = requests.get(
                        f"https://api.notion.com/v1/databases/{child_db_id}",
                        headers=headers,
                        timeout=10,
                    )
                    if child_db_resp.status_code == 200:
                        db_id, ds_id, props = _extract_from_db_object(child_db_resp.json())
                        return db_id, ds_id, props, None
                    return child_db_id, None, {}, None
        elif resp.status_code in (401, 403):
            return None, None, None, "Unauthorized: Notion API key does not have access to the page."
        elif resp.status_code == 404:
            return None, None, None, "Notion page not found. Please verify NOTION_PAGE_ID."
    except Exception as e:
        return None, None, None, f"Network error connecting to Notion API: {str(e)}"

    # 4. Fallback search endpoint
    search_url = "https://api.notion.com/v1/search"
    try:
        resp = requests.post(search_url, headers=headers, json={"page_size": 20}, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for item in results:
                obj_type = item.get("object")
                if obj_type == "data_source":
                    ds_id = item.get("id")
                    props = item.get("properties", {})
                    db_id = (item.get("parent") or {}).get("database_id", ds_id)
                    return db_id, ds_id, props, None
                elif obj_type == "database":
                    db_id, ds_id, props = _extract_from_db_object(item)
                    return db_id, ds_id, props, None
    except Exception:
        pass

    return None, None, None, f"Could not find a Notion database for page ID {page_id}."


def locate_notion_database(
    api_key: str, page_id: str, version: Optional[str] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """Legacy helper returning (db_id_or_ds_id, schema, error)."""
    db_id, ds_id, schema, err = locate_notion_target(api_key, page_id, version)
    return ds_id or db_id, schema, err


def get_notion_status() -> Tuple[Dict[str, Any], int]:
    """
    GET /api/notion/status
    Safely reports whether Notion configuration and database access are usable.
    """
    load_dotenv()
    api_key = os.getenv("NOTION_API_KEY", "").strip()
    page_id = os.getenv("NOTION_PAGE_ID", "").strip()

    if not api_key or not page_id:
        return {
            "configured": False,
            "usable": False,
            "error": "NOTION_API_KEY or NOTION_PAGE_ID is missing in configuration.",
        }, 200

    db_id, ds_id, schema, err = locate_notion_target(api_key, page_id)
    if err or (not db_id and not ds_id):
        return {
            "configured": True,
            "usable": False,
            "error": err or "Failed to locate database on Notion page.",
        }, 200

    return {
        "configured": True,
        "usable": True,
        "database_id": db_id,
        "data_source_id": ds_id,
        "message": "Notion API configuration and database access are ready.",
    }, 200


def _parse_time_slot(item: Dict[str, Any]) -> Tuple[str, str]:
    """Extract start_time and end_time strings from item or time_slot."""
    start_time = item.get("start_time", "")
    end_time = item.get("end_time", "")
    if start_time and end_time:
        return str(start_time).strip(), str(end_time).strip()

    slot = str(item.get("time_slot", "")).strip()
    if not slot:
        return "", ""

    parts = re.split(r"\s*[\u2013\u2014-]\s*", slot)
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    elif len(parts) == 1:
        return parts[0].strip(), ""
    return "", ""


def _get_item_date(item: Dict[str, Any], default_date: Optional[str] = None) -> str:
    """Retrieve date for schedule item in YYYY-MM-DD format."""
    item_date = item.get("date")
    if item_date:
        return str(item_date).strip()
    if default_date:
        return str(default_date).strip()
    return datetime.date.today().isoformat()


def _get_safe_select_value(raw_val: Any, prop_schema: Dict[str, Any]) -> Optional[str]:
    """Format select value and match case-insensitively against existing schema options if present."""
    if not raw_val:
        return None
    s_val = str(raw_val).strip()
    if not s_val:
        return None

    formatted_val = s_val.replace("_", " ").title()

    options = []
    if isinstance(prop_schema, dict) and prop_schema.get("type") == "select":
        select_dict = prop_schema.get("select") or {}
        options = select_dict.get("options") or []

    for opt in options:
        opt_name = opt.get("name", "")
        if opt_name.lower() == s_val.lower() or opt_name.lower() == formatted_val.lower():
            return opt_name

    return formatted_val


def _resolve_schema_properties(schema: Dict[str, Any]) -> Dict[str, str]:
    """
    Map schema keys for Name, Date, Start Time, End Time, Type, Priority, Description.
    Preserves exact original key names (including trailing spaces).
    """
    resolved: Dict[str, str] = {}
    if not isinstance(schema, dict):
        return resolved

    for prop_name, prop_info in schema.items():
        if not isinstance(prop_info, dict):
            continue
        p_type = prop_info.get("type", "")
        p_name_clean = prop_name.strip().lower()

        if p_type == "title" or p_name_clean == "name":
            if "name" not in resolved or p_type == "title":
                resolved["name"] = prop_name
        elif p_type == "date" or p_name_clean == "date":
            if "date" not in resolved or p_type == "date":
                resolved["date"] = prop_name
        elif p_name_clean in ("start time", "start_time", "starttime"):
            resolved["start_time"] = prop_name
        elif p_name_clean in ("end time", "end_time", "endtime"):
            resolved["end_time"] = prop_name
        elif p_name_clean == "type":
            resolved["type"] = prop_name
        elif p_name_clean == "priority":
            resolved["priority"] = prop_name
        elif p_name_clean in ("description", "notes"):
            resolved["description"] = prop_name

    defaults = {
        "name": "Name",
        "date": "Date",
        "start_time": "Start Time",
        "end_time": "End Time",
        "type": "Type",
        "priority": "Priority",
        "description": "Description",
    }
    for key, default_name in defaults.items():
        if key not in resolved and default_name in schema:
            resolved[key] = default_name

    return resolved


def export_schedule_to_notion(data: Any) -> Tuple[Dict[str, Any], int]:
    """
    POST /api/notion/export
    Exports schedule items to the Notion database / data source.
    """
    load_dotenv()
    api_key = os.getenv("NOTION_API_KEY", "").strip()
    page_id = os.getenv("NOTION_PAGE_ID", "").strip()

    if not api_key or not page_id:
        return {
            "success": False,
            "error": "NOTION_API_KEY or NOTION_PAGE_ID is missing in configuration.",
        }, 400

    schedule = None
    default_date = None
    if isinstance(data, dict):
        schedule = data.get("schedule")
        if schedule is None and isinstance(data.get("plan"), dict):
            schedule = data["plan"].get("schedule")
        default_date = data.get("date")
    elif isinstance(data, list):
        schedule = data

    if not isinstance(schedule, list) or len(schedule) == 0:
        return {
            "success": False,
            "error": "Missing or empty 'schedule' in request payload.",
        }, 400

    db_id, ds_id, schema, err = locate_notion_target(api_key, page_id)
    if err or (not db_id and not ds_id):
        return {
            "success": False,
            "error": err or "Failed to locate database/data_source on Notion page.",
        }, 400

    headers = get_notion_headers(api_key)
    prop_map = _resolve_schema_properties(schema or {})

    # Parent construction: prefer data_source_id if available, fallback to database_id
    if ds_id:
        parent_payload = {"data_source_id": ds_id}
    else:
        parent_payload = {"database_id": db_id}

    exported_count = 0
    created_pages: List[str] = []
    errors: List[str] = []

    for item in schedule:
        if not isinstance(item, dict):
            continue

        title = item.get("title") or item.get("name") or "Untitled Task"
        start_time, end_time = _parse_time_slot(item)
        item_date = _get_item_date(item, default_date)
        raw_type = item.get("type", "")
        raw_priority = item.get("priority", "")
        description = item.get("notes") or item.get("description") or ""

        type_val = _get_safe_select_value(
            raw_type, (schema or {}).get(prop_map.get("type", ""), {})
        )
        priority_val = _get_safe_select_value(
            raw_priority, (schema or {}).get(prop_map.get("priority", ""), {})
        )

        page_props: Dict[str, Any] = {}

        if prop_map.get("name"):
            page_props[prop_map["name"]] = {"title": [{"text": {"content": str(title)}}]}

        if prop_map.get("date") and item_date:
            page_props[prop_map["date"]] = {"date": {"start": item_date}}

        if prop_map.get("start_time") and start_time:
            page_props[prop_map["start_time"]] = {
                "rich_text": [{"text": {"content": str(start_time)}}]
            }

        if prop_map.get("end_time") and end_time:
            page_props[prop_map["end_time"]] = {
                "rich_text": [{"text": {"content": str(end_time)}}]
            }

        if prop_map.get("type") and type_val:
            page_props[prop_map["type"]] = {"select": {"name": type_val}}

        if prop_map.get("priority") and priority_val:
            page_props[prop_map["priority"]] = {"select": {"name": priority_val}}

        if prop_map.get("description") and description:
            page_props[prop_map["description"]] = {
                "rich_text": [{"text": {"content": str(description)}}]
            }

        create_payload = {"parent": parent_payload, "properties": page_props}

        try:
            resp = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=create_payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                exported_count += 1
                page_data = resp.json()
                if page_data.get("id"):
                    created_pages.append(page_data["id"])
            else:
                # Fallback attempt without select fields if select option creation rejected
                fb_props = {
                    k: v
                    for k, v in page_props.items()
                    if k not in (prop_map.get("type"), prop_map.get("priority"))
                }
                fb_payload = {"parent": parent_payload, "properties": fb_props}
                fb_resp = requests.post(
                    "https://api.notion.com/v1/pages",
                    headers=headers,
                    json=fb_payload,
                    timeout=15,
                )
                if fb_resp.status_code in (200, 201):
                    exported_count += 1
                    fb_data = fb_resp.json()
                    if fb_data.get("id"):
                        created_pages.append(fb_data["id"])
                else:
                    err_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    err_msg = err_data.get("message", resp.text)
                    errors.append(f"Failed to export '{title}': {err_msg}")
        except Exception as e:
            errors.append(f"Exception exporting '{title}': {str(e)}")

    if exported_count > 0:
        msg = f"Successfully exported {exported_count} item(s) to Notion."
        if errors:
            msg += f" ({len(errors)} item(s) failed)."
        return {
            "success": True,
            "message": msg,
            "exported_count": exported_count,
            "created_pages": created_pages,
        }, 200
    else:
        first_err = errors[0] if errors else "Failed to export schedule items to Notion."
        return {
            "success": False,
            "error": first_err,
            "exported_count": 0,
        }, 500
