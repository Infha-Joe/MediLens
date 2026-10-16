import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import ObjectId
from bson.errors import InvalidId
from flask import (Blueprint, abort, jsonify, current_app, flash, redirect,
                   render_template, request, send_from_directory, session, url_for)

from auth import role_required
from db import get_db
from geo import haversine_km, is_open
from ocr import extract_text, match_medicines

bp = Blueprint("user", __name__, url_prefix="/user")
ALLOWED = {"jpg", "jpeg", "png", "webp"}


def _oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        abort(404)


def _log(medicine_id, source, photo=None):
    """Save to search history (skips a repeat within 60 seconds)."""
    db, uid = get_db(), ObjectId(session["user_id"])
    since = datetime.now(timezone.utc) - timedelta(seconds=60)
    if db.search_history.find_one({"user_id": uid, "medicine_id": medicine_id,
                                   "created_at": {"$gt": since}}):
        return
    db.search_history.insert_one({"user_id": uid, "medicine_id": medicine_id,
                                  "source": source, "photo": photo,
                                  "created_at": datetime.now(timezone.utc)})


def _history(limit):
    db, rows = get_db(), []
    for h in db.search_history.find({"user_id": ObjectId(session["user_id"])}) \
                              .sort("created_at", -1).limit(limit):
        med = db.medicines.find_one({"_id": h["medicine_id"]})
        if med:
            rows.append({"med": med, **h})
    return rows


@bp.route("/")
@role_required("user")
def home():
    return render_template("user_home.html", recent=_history(5))


@bp.route("/scan", methods=["POST"])
@role_required("user")
def scan():
    file = request.files.get("photo")
    ext = (file.filename.rsplit(".", 1)[-1].lower() if file and "." in file.filename else "")
    if ext not in ALLOWED:
        flash("Upload a photo in JPG, PNG, or WEBP format.", "error")
        return redirect(url_for("user.home"))

    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], name)
    file.save(path)

    text = extract_text(path)
    if not text.strip():
        flash("We couldn't read any text. Retake the photo in good light, or search by name.", "error")
        return redirect(url_for("user.home"))

    found = match_medicines(list(get_db().medicines.find()), text)
    strong = [m for s, m in found if s >= 0.9]
    if len(strong) == 1:  # one clear match: go straight to it
        return redirect(url_for("user.medicine", mid=strong[0]["_id"], src="scan", photo=name))
    return render_template("scan_result.html", found=found, photo=name)


@bp.route("/search")
@role_required("user")
def search():
    q = request.args.get("q", "").strip()
    results = []
    is_random = False
    
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        results = list(get_db().medicines.find({"$or": [{"brand": rx}, {"salt": rx}]}).limit(20))
    else:
        results = list(get_db().medicines.aggregate([{"$sample": {"size": 8}}]))
        is_random = True
        
    return render_template("search.html", q=q, results=results, is_random=is_random)

def view_fields(med, lang):
    """Medicine text in the chosen language, falling back to English."""
    tr = (med.get("i18n") or {}).get(lang) or {}
    return {k: tr.get(k) or med.get(k, "") for k in ("uses", "side_effects", "warnings")}, bool(tr)



@bp.route("/medicine/<mid>")
@role_required("user")
def medicine(mid):
    db, oid = get_db(), _oid(mid)
    med = db.medicines.find_one({"_id": oid})
    if not med:
        abort(404)
    alts = list(db.medicines.find({"salt": med["salt"], "strength": med["strength"],
                                   "_id": {"$ne": oid}}).sort("mrp", 1))
    for a in alts:
        a["saving"] = round((med["mrp"] - a["mrp"]) / med["mrp"] * 100) if med["mrp"] else 0
    src = request.args.get("src")
    if src in ("scan", "search"):
        _log(oid, src, request.args.get("photo"))
    view, translated = view_fields(med, session.get("lang", "en"))
    return render_template("medicine.html", med=med, alts=alts, offers=_offers(db, oid),
                           view=view, translated=translated)


@bp.route("/history")
@role_required("user")
def history():
    return render_template("history.html", rows=_history(100))


@bp.route("/photo/<name>")
@role_required("user")
def photo(name):
    owned = get_db().search_history.find_one(
        {"user_id": ObjectId(session["user_id"]), "photo": name})
    if not owned:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)


def _offers(db, med_id):
    out = []
    for inv in db.inventory.find({"medicine_id": med_id, "qty": {"$gt": 0}}).sort("price", 1):
        shop = db.shops.find_one({"_id": inv["shop_id"]})
        owner = db.users.find_one({"_id": shop["user_id"]}) if shop else None
        if owner and owner["status"] == "approved":
            out.append({"shop": shop, "inv": inv})
    return out






@bp.route("/shops")
@role_required("user")
def shops():
    db = get_db()
    mid = request.args.get("mid")
    med = db.medicines.find_one({"_id": _oid(mid)}) if mid else None
    
    # Get all medicines for dropdown (sorted by brand)
    all_medicines = list(db.medicines.find({}, {"brand": 1, "strength": 1, "salt": 1}).sort("brand", 1))
    
    cities = db.shops.distinct("city")
    cities = [c for c in cities if c and c not in ["1", "2", "3", "Unknown"]]
    cities = sorted(cities)
    return render_template("shops.html", med=med, cities=cities, all_medicines=all_medicines)


@bp.route("/shops/data")
@role_required("user")
def shops_data():
    db = get_db()
    a = request.args
    mid = _oid(a.get("mid"))
    
    now = datetime.now(ZoneInfo(current_app.config["TIMEZONE"]))
    rows = []
    
    city_filter = a.get("city", "")
    shop_query = {}
    
    if city_filter and city_filter != "All Cities":
        shop_query["city"] = city_filter
        
    shops = db.shops.find(shop_query)
    
    for s in shops:
        inv = db.inventory.find_one({"shop_id": s["_id"], "medicine_id": mid, "qty": {"$gt": 0}})
        owner = db.users.find_one({"_id": s["user_id"]})
        if not inv or not owner or owner["status"] != "approved":
            continue
            

        opn = is_open(s.get("hours"), now)
        if a.get("open_now") == "1" and opn is False:
            continue
            
        rows.append({
            "id": str(s["_id"]),
            "name": s["name"],
            "address": s["address"],
            "phone": s.get("phone", ""),
            "hours": s.get("hours", ""),
            "delivery": bool(s.get("delivery")),
            "open": opn,
            "price": inv["price"],
            "qty": inv["qty"]
        })
        
    # Sort by price primarily since distance is removed
    rows.sort(key=lambda r: r["price"])
    return jsonify(shops=rows)

@bp.route("/pharmacy/<shop_id>")
@role_required("user")
def pharmacy_details(shop_id):
    db = get_db()
    shop = db.shops.find_one({"_id": _oid(shop_id)})
    if not shop:
        flash("Pharmacy not found.", "error")
        return redirect(url_for("user.shops"))
    
    inventory_cursor = db.inventory.find({"shop_id": shop["_id"], "qty": {"$gt": 0}})
    inventory_items = []
    for inv in inventory_cursor:
        med = db.medicines.find_one({"_id": inv["medicine_id"]})
        if med:
            inventory_items.append({"med": med, "inv": inv})
            
    back_city = request.args.get("city", "")
    back_mid = request.args.get("mid", "")
    
    return render_template("pharmacy_details.html", shop=shop, inventory=inventory_items, back_city=back_city, back_mid=back_mid)
