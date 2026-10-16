from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, send_from_directory, session, url_for)

from auth import role_required
from db import get_db

bp = Blueprint("shop", __name__, url_prefix="/shop")
FLOW = {"accept": ("placed", "accepted"), "reject": ("placed", "rejected"),
        "ready": ("accepted", "ready"), "complete": ("ready", "completed")}


def _oid(v):
    try:
        return ObjectId(v)
    except (InvalidId, TypeError):
        abort(404)


def _shop():
    s = get_db().shops.find_one({"user_id": ObjectId(session["user_id"])})
    if not s:
        abort(404)
    return s


@bp.route("/")
@role_required("shop")
def home():
    db, s = get_db(), _shop()
    stats = {"Medicines in stock": db.inventory.count_documents({"shop_id": s["_id"], "qty": {"$gt": 0}}),
             "Low stock (5 or fewer)": db.inventory.count_documents({"shop_id": s["_id"], "qty": {"$lte": 5}}),
             "New orders": db.orders.count_documents({"shop_id": s["_id"], "status": "placed"})}
    return render_template("shop_home.html", shop=s, stats=stats)


@bp.route("/stock")
@role_required("shop")
def stock():
    db, s = get_db(), _shop()
    items = []
    for inv in db.inventory.find({"shop_id": s["_id"]}):
        med = db.medicines.find_one({"_id": inv["medicine_id"]})
        if med:
            items.append({"inv": inv, "med": med})
    items.sort(key=lambda i: i["med"]["brand"])
    return render_template("shop_stock.html", items=items,
                           meds=db.medicines.find().sort("brand", 1))


def _price_qty():
    try:
        price, qty = float(request.form["price"]), int(request.form["qty"])
        assert price > 0 and qty >= 0
        return price, qty
    except (KeyError, ValueError, AssertionError):
        return None


@bp.route("/stock/add", methods=["POST"])
@role_required("shop")
def stock_add():
    s, pq = _shop(), _price_qty()
    mid = _oid(request.form.get("medicine_id"))
    if not pq or not get_db().medicines.find_one({"_id": mid}):
        flash("Choose a medicine, a price above 0, and a quantity of 0 or more.", "error")
    else:
        get_db().inventory.update_one({"shop_id": s["_id"], "medicine_id": mid},
            {"$set": {"price": pq[0], "qty": pq[1], "updated_at": datetime.now(timezone.utc)}}, upsert=True)
        flash("Stock saved.", "success")
    return redirect(url_for("shop.stock"))


@bp.route("/stock/<iid>/update", methods=["POST"])
@role_required("shop")
def stock_update(iid):
    s, pq = _shop(), _price_qty()
    if not pq:
        flash("Enter a price above 0 and a quantity of 0 or more.", "error")
    else:
        get_db().inventory.update_one({"_id": _oid(iid), "shop_id": s["_id"]},
            {"$set": {"price": pq[0], "qty": pq[1], "updated_at": datetime.now(timezone.utc)}})
        flash("Stock updated.", "success")
    return redirect(url_for("shop.stock"))


@bp.route("/stock/<iid>/delete", methods=["POST"])
@role_required("shop")
def stock_delete(iid):
    get_db().inventory.delete_one({"_id": _oid(iid), "shop_id": _shop()["_id"]})
    flash("Removed from your stock.", "success")
    return redirect(url_for("shop.stock"))


@bp.route("/orders")
@role_required("shop")
def orders():
    db, rows = get_db(), []
    for o in db.orders.find({"shop_id": _shop()["_id"]}).sort("created_at", -1):
        rows.append({**o, "med": db.medicines.find_one({"_id": o["medicine_id"]}),
                     "customer": db.users.find_one({"_id": o["user_id"]})})
    return render_template("shop_orders.html", rows=rows)


@bp.route("/orders/<oid>/<action>", methods=["POST"])
@role_required("shop")
def order_action(oid, action):
    db, s = get_db(), _shop()
    o = db.orders.find_one({"_id": _oid(oid), "shop_id": s["_id"]})
    if not o or action not in FLOW or o["status"] != FLOW[action][0]:
        flash("That order can't be changed that way.", "error")
        return redirect(url_for("shop.orders"))
    if action == "accept":  # reserve the stock atomically
        ok = db.inventory.update_one({"shop_id": s["_id"], "medicine_id": o["medicine_id"],
                                      "qty": {"$gte": o["qty"]}}, {"$inc": {"qty": -o["qty"]}})
        if not ok.modified_count:
            flash("Not enough stock to accept this order. Update your stock first.", "error")
            return redirect(url_for("shop.orders"))
    db.orders.update_one({"_id": o["_id"]}, {"$set": {"status": FLOW[action][1]}})
    flash(f"Order marked {FLOW[action][1]}.", "success")
    return redirect(url_for("shop.orders"))


@bp.route("/prescription/<name>")
@role_required("shop")
def prescription(name):
    if not get_db().orders.find_one({"shop_id": _shop()["_id"], "prescription": name}):
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)


@bp.route("/profile", methods=["GET", "POST"])
@role_required("shop")
def profile():
    s = _shop()
    if request.method == "POST":
        f = request.form
        get_db().shops.update_one({"_id": s["_id"]}, {"$set": {
            "phone": f.get("phone", "").strip(), "hours": f.get("hours", "").strip(),
            "address": f.get("address", "").strip(), "delivery": f.get("delivery") == "on"}})
        flash("Shop details saved.", "success")
        return redirect(url_for("shop.profile"))
    return render_template("shop_profile.html", shop=s)
