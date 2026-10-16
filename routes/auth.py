"""
Auth routes — registration, login, logout, password reset, onboarding,
alerts, and notifications.
"""
from flask import Blueprint, jsonify, request, session, render_template, send_from_directory, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import uuid

from db import (
    create_user, get_user_by_email, get_user_by_id,
    set_reset_token, get_user_by_reset_token, update_password,
    get_user_preferences, update_user_preferences,
    add_alert, get_user_alerts, deactivate_alert,
    create_notification, get_user_notifications, mark_notifications_read,
)

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Shared decorator
# ---------------------------------------------------------------------------
def login_required(f):
    """Decorator for routes that require login."""
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@auth_bp.route("/api/auth/status")
def auth_status():
    if "user_id" in session:
        prefs = get_user_preferences(session["user_id"])
        needs_onboarding = not bool(prefs)
        return jsonify({
            "logged_in": True,
            "user": {"name": session.get("user_name")},
            "needs_onboarding": needs_onboarding,
            "preferences": prefs,
        }), 200
    return jsonify({"logged_in": False}), 200


@auth_bp.route("/auth")
def auth_page():
    """Serve authentication page."""
    if "user_id" in session:
        return send_from_directory(current_app.template_folder, "index.html")
    return render_template("auth.html")


@auth_bp.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm = data.get("confirm_password", "")
    name = data.get("name", "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    hashed = generate_password_hash(password)
    if create_user(email, hashed, name):
        return jsonify({"message": "Account created"}), 201
    return jsonify({"error": "Registration failed"}), 500


@auth_bp.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["user_name"] = user["first_name"]
        prefs = get_user_preferences(user["id"])
        return jsonify({
            "message": "Logged in",
            "user": {"name": user["first_name"]},
            "needs_onboarding": not bool(prefs),
        }), 200
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    user = get_user_by_email(email)
    if user:
        token = uuid.uuid4().hex
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        set_reset_token(email, token, expiry)
    return jsonify({"message": "If email exists, token sent."}), 200


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    data = request.json or {}
    token = data.get("token", "")
    new_password = data.get("new_password", "")

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    user = get_user_by_reset_token(token)
    if not user:
        return jsonify({"error": "Invalid token"}), 400

    expiry_str = user.get("reset_token_expiry")
    if not expiry_str:
        return jsonify({"error": "Invalid token"}), 400

    try:
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now(timezone.utc) > expiry:
            return jsonify({"error": "Token expired"}), 400
    except ValueError:
        return jsonify({"error": "Invalid token expiry"}), 400

    hashed = generate_password_hash(new_password)
    update_password(user["id"], hashed)
    return jsonify({"message": "Password reset successful"}), 200


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------
@auth_bp.route("/onboarding")
@login_required
def onboarding_page():
    return render_template("onboarding.html")


@auth_bp.route("/api/onboarding", methods=["POST"])
@login_required
def api_onboarding():
    data = request.json or {}
    experience = data.get("experience", "Beginner")
    goals = data.get("goals", [])
    sectors = data.get("sectors", [])
    update_user_preferences(session["user_id"], experience, goals, sectors)
    return jsonify({"message": "Preferences saved successfully"}), 200


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
@auth_bp.route("/api/alerts", methods=["GET", "POST", "DELETE"])
@login_required
def api_alerts():
    user_id = session["user_id"]
    if request.method == "GET":
        alerts = get_user_alerts(user_id)
        return jsonify({"alerts": alerts}), 200

    if request.method == "POST":
        data = request.json or {}
        symbol = data.get("symbol")
        ctype = data.get("condition_type")
        threshold = data.get("threshold")
        if not symbol or not ctype or threshold is None:
            return jsonify({"error": "Missing parameters"}), 400
        try:
            add_alert(user_id, symbol, ctype, float(threshold))
            return jsonify({"message": "Alert added successfully"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        data = request.json or {}
        alert_id = data.get("alert_id")
        if not alert_id:
            return jsonify({"error": "Missing alert_id"}), 400
        deactivate_alert(alert_id)
        return jsonify({"message": "Alert deactivated"}), 200


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
@auth_bp.route("/api/notifications", methods=["GET"])
@login_required
def api_notifications():
    unread_only = request.args.get("unread", "true").lower() == "true"
    notifs = get_user_notifications(session["user_id"], unread_only)
    return jsonify({"notifications": notifs, "count": len(notifs)}), 200


@auth_bp.route("/api/notifications/read", methods=["POST"])
@login_required
def api_notifications_read():
    mark_notifications_read(session["user_id"])
    return jsonify({"message": "Notifications marked as read"}), 200
