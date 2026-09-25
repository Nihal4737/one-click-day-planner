import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect
from flask_cors import CORS

# Load environment variables from backend/.env immediately before module initialization
load_dotenv()

from planner import generate_day_plan
from calendar_service import (
    get_auth_url,
    handle_oauth_callback,
    load_valid_token,
    export_schedule_to_calendar
)
from notion_service import get_notion_status, export_schedule_to_notion

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "One-Click Day Planner API is running",
        "version": "1.0.0"
    }), 200


@app.route("/api/generate-plan", methods=["POST"])
def handle_generate_plan():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    result, status_code = generate_day_plan(data)
    return jsonify(result), status_code


@app.route("/api/calendar/auth", methods=["GET"])
def handle_calendar_auth():
    auth_url, error = get_auth_url()
    if error:
        return jsonify({"error": error}), 400
    
    # If opened directly in browser window, redirect immediately
    if "text/html" in request.headers.get("Accept", ""):
        return redirect(auth_url)
    
    return jsonify({"auth_url": auth_url}), 200


@app.route("/api/calendar/callback", methods=["GET"])
def handle_calendar_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    success, message = handle_oauth_callback(code)
    if not success:
        return jsonify({"error": message}), 400

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return redirect(f"{frontend_url}?calendar_auth=success")


@app.route("/api/calendar/status", methods=["GET"])
def handle_calendar_status():
    token, error = load_valid_token()
    return jsonify({"authenticated": token is not None, "error": error}), 200


@app.route("/api/calendar/export", methods=["POST"])
def handle_calendar_export():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    schedule = data.get("schedule")
    if schedule is None and isinstance(data.get("plan"), dict):
        schedule = data["plan"].get("schedule")
    if schedule is None and isinstance(data, list):
        schedule = data

    if schedule is None:
        return jsonify({"error": "Missing 'schedule' in request payload"}), 400

    result, status_code = export_schedule_to_calendar(schedule)
    return jsonify(result), status_code


@app.route("/api/notion/status", methods=["GET"])
def handle_notion_status():
    result, status_code = get_notion_status()
    return jsonify(result), status_code


@app.route("/api/notion/export", methods=["POST"])
def handle_notion_export():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    schedule = data.get("schedule")
    if schedule is None and isinstance(data.get("plan"), dict):
        schedule = data["plan"].get("schedule")
    if schedule is None and isinstance(data, list):
        schedule = data

    if schedule is None:
        return jsonify({"error": "Missing 'schedule' in request payload"}), 400

    result, status_code = export_schedule_to_notion(data)
    return jsonify(result), status_code


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)

