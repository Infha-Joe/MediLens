from datetime import datetime, timezone
from functools import wraps

from bson import ObjectId
from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

bp = Blueprint("auth", __name__)
HOME = {"user": "user.home", "shop": "shop.home", "admin": "admin.home"}


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return f(*a, **kw)
    return wrapper


def role_required(*roles):
    def deco(f):
        @wraps(f)
        @login_required
        def wrapper(*a, **kw):
            if session.get("role") not in roles:
                flash("You don't have access to that page.", "error")
                return redirect(url_for("index"))
            return f(*a, **kw)
        return wrapper
    return deco


def _now():
    return datetime.now(timezone.utc)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    db = get_db()
    f = request.form
    name, email = f.get("name", "").strip(), f.get("email", "").strip().lower()
    password, role = f.get("password", ""), f.get("role", "user")

    if role not in ("user", "shop"):  # admin can never self-register
        role = "user"
    if not name or not email or len(password) < 8:
        flash("Enter your name, email, and a password of at least 8 characters.", "error")
        return render_template("register.html"), 400
    if db.users.find_one({"email": email}):
        flash("That email is already registered. Log in instead.", "error")
        return render_template("register.html"), 400

    shop_data = None
    if role == "shop":
        try:
            lat, lng = float(f["lat"]), float(f["lng"])
            assert -90 <= lat <= 90 and -180 <= lng <= 180
        except (KeyError, ValueError, AssertionError):
            flash("Pin your shop location using the 'Use my location' button.", "error")
            return render_template("register.html"), 400
        shop_data = {
            "name": f.get("shop_name", "").strip(),
            "address": f.get("address", "").strip(),
            "city": f.get("city", "").strip(),
            "license_no": f.get("license_no", "").strip(),
            "phone": f.get("phone", "").strip(),
            "hours": f.get("hours", "").strip(),
            "location": {"type": "Point", "coordinates": [lng, lat]},
        }
        if not all([shop_data["name"], shop_data["address"], shop_data["license_no"]]):
            flash("Shop name, address, and license number are required.", "error")
            return render_template("register.html"), 400

    uid = db.users.insert_one({
        "name": name, "email": email,
        "password_hash": generate_password_hash(password),
        "role": role,
        "status": "pending" if role == "shop" else "approved",
        "created_at": _now(),
    }).inserted_id
    if shop_data:
        db.shops.insert_one({**shop_data, "user_id": uid, "created_at": _now()})
        flash("Shop registered. You can log in once an admin approves it.", "success")
    else:
        flash("Account created. Log in to start.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    user = get_db().users.find_one({"email": email})
    
    if not user:
        flash("Email or password is incorrect.", "error")
        return render_template("login.html"), 401

    if user.get("auth_provider") == "google":
        flash("This account uses Google Sign-In. Please continue with Google.", "error")
        return render_template("login.html"), 401

    password_hash = user.get("password_hash")
    if not password_hash:
        flash("Your account does not have a password configured. Please use password reset.", "error")
        return render_template("login.html"), 401

    if not check_password_hash(password_hash, request.form.get("password", "")):
        flash("Email or password is incorrect.", "error")
        return render_template("login.html"), 401
    if user["status"] == "pending":
        flash("Your shop is waiting for admin approval.", "error")
        return render_template("login.html"), 403
    if user["status"] == "blocked":
        flash("This account has been blocked. Contact the admin.", "error")
        return render_template("login.html"), 403

    session.clear()
    session.update(user_id=str(user["_id"]), role=user["role"], name=user["name"],
                   lang=user.get("lang", "en"))
    return redirect(url_for(HOME[user["role"]]))


@bp.route("/logout")
def logout():
    session.clear()
    flash("You're logged out.", "success")
    return redirect(url_for("auth.login"))
