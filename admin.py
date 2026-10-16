from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
import re

from auth import role_required
from db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _oid(v):
    try:
        return ObjectId(v)
    except (InvalidId, TypeError):
        abort(404)


@bp.route("/")
@role_required("admin")
def home():
    db = get_db()
    stats = {"Pending shops": db.users.count_documents({"role": "shop", "status": "pending"}),
             "Approved shops": db.users.count_documents({"role": "shop", "status": "approved"}),
             "Customers": db.users.count_documents({"role": "user"}),
             "Medicines": db.medicines.count_documents({}),
             "Orders": db.orders.count_documents({})}
    return render_template("admin_home.html", stats=stats)


@bp.route("/shops")
@role_required("admin")
def shops():
    db, rows = get_db(), []
    for u in db.users.find({"role": "shop"}).sort("created_at", -1):
        rows.append({"id": str(u["_id"]), "email": u["email"], "status": u["status"],
                     **(db.shops.find_one({"user_id": u["_id"]}) or {})})
    return render_template("admin_shops.html", rows=rows)


@bp.route("/shops/<uid>/<action>", methods=["POST"])
@role_required("admin")
def shop_action(uid, action):
    status = {"approve": "approved", "block": "blocked", "reject": "blocked"}.get(action)
    if status:
        get_db().users.update_one({"_id": _oid(uid), "role": "shop"}, {"$set": {"status": status}})
        flash(f"Shop {status}.", "success")
    return redirect(url_for("admin.shops"))


@bp.route("/users")
@role_required("admin")
def users():
    return render_template("admin_users.html", rows=get_db().users.find({"role": "user"}).sort("created_at", -1))


@bp.route("/users/<uid>/toggle", methods=["POST"])
@role_required("admin")
def user_toggle(uid):
    db, u = get_db(), get_db().users.find_one({"_id": _oid(uid), "role": "user"})
    if u:
        db.users.update_one({"_id": u["_id"]}, {"$set": {"status": "approved" if u["status"] == "blocked" else "blocked"}})
        flash("User updated.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/medicines")
@role_required("admin")
def medicines():
    q = request.args.get("q", "").strip()
    flt = {"$or": [{"brand": {"$regex": re.escape(q), "$options": "i"}},
                   {"salt": {"$regex": re.escape(q), "$options": "i"}}]} if q else {}
    return render_template("admin_medicines.html", meds=get_db().medicines.find(flt).sort("brand", 1), q=q)


def _med_form():
    f = request.form
    try:
        med = {"brand": f["brand"].strip(), "salt": f["salt"].strip().lower(),
               "strength": f["strength"].strip(), "mrp": float(f["mrp"]),
               "uses": f["uses"].strip(), "side_effects": f["side_effects"].strip(),
               "warnings": f["warnings"].strip(), "rx_required": f.get("rx_required") == "on"}
        assert all([med["brand"], med["salt"], med["strength"], med["uses"]]) and med["mrp"] > 0
        return med
    except (KeyError, ValueError, AssertionError):
        return None


@bp.route("/medicines/new", methods=["GET", "POST"])
@role_required("admin")
def medicine_new():
    if request.method == "POST":
        med = _med_form()
        if med:
            get_db().medicines.insert_one(med)
            flash("Medicine added.", "success")
            return redirect(url_for("admin.medicines"))
        flash("Brand, salt, strength, MRP (above 0), and uses are required.", "error")
    return render_template("admin_medicine_form.html", med=request.form or {})


@bp.route("/medicines/<mid>/edit", methods=["GET", "POST"])
@role_required("admin")
def medicine_edit(mid):
    db, oid = get_db(), _oid(mid)
    med = db.medicines.find_one({"_id": oid}) or abort(404)
    if request.method == "POST":
        new = _med_form()
        if new:
            db.medicines.update_one({"_id": oid}, {"$set": new})
            flash("Medicine updated.", "success")
            return redirect(url_for("admin.medicines"))
        flash("Brand, salt, strength, MRP (above 0), and uses are required.", "error")
    return render_template("admin_medicine_form.html", med=med, edit=True)


@bp.route("/medicines/<mid>/delete", methods=["POST"])
@role_required("admin")
def medicine_delete(mid):
    db, oid = get_db(), _oid(mid)
    if db.inventory.count_documents({"medicine_id": oid}) or db.orders.count_documents({"medicine_id": oid}):
        flash("This medicine is in shop stock or orders, so it can't be deleted.", "error")
    else:
        db.medicines.delete_one({"_id": oid})
        flash("Medicine deleted.", "success")
    return redirect(url_for("admin.medicines"))

import gridfs
from datetime import datetime, timezone
import re
from werkzeug.utils import secure_filename

@bp.route("/health_tips")
@role_required("admin")
def health_tips():
    db = get_db()
    category = request.args.get("category", "")
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "newest")

    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    if q:
        query["content.en.title"] = {"$regex": re.escape(q), "$options": "i"}

    # Actual PyMongo Queries for Faculty Demo
    # e.g., Filter active Nutrition tips: {"$and": [{"category": "Nutrition"}, {"status": "active"}]}
    if category and status:
        query = {"$and": [{"category": category}, {"status": status}]}
    
    # Meaningful sorting
    sort_order = [("created_at", -1)]
    if sort_by == "oldest":
        sort_order = [("created_at", 1)]
    elif sort_by == "a-z":
        sort_order = [("content.en.title", 1)]
    elif sort_by == "z-a":
        sort_order = [("content.en.title", -1)]

    tips = list(db.health_tips.find(query).sort(sort_order))
    return render_template("admin_health_tips.html", tips=tips, filters=request.args)

@bp.route("/health_tips/new", methods=["GET", "POST"])
@role_required("admin")
def health_tip_new():
    db = get_db()
    fs = gridfs.GridFS(db)
    if request.method == "POST":
        f = request.form
        file = request.files.get("image")
        
        file_id = None
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_id = fs.put(file, filename=filename, content_type=file.content_type)
        
        doc = {
            "category": f.get("category", ""),
            "content": {
                "en": {"title": f.get("en_title", ""), "description": f.get("en_text", "")},
                "ta": {"title": f.get("ta_title", ""), "description": f.get("ta_text", "")},
                "hi": {"title": f.get("hi_title", ""), "description": f.get("hi_text", "")}
            },
            "status": f.get("status", "active"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        if file_id:
            doc["media"] = {
                "type": "image",
                "file_id": file_id,
                "filename": filename,
                "mime_type": file.content_type
            }
            
        db.health_tips.insert_one(doc)
        flash("Health tip created successfully.", "success")
        return redirect(url_for("admin.health_tips"))
        
    return render_template("admin_health_tip_form.html", tip={})

@bp.route("/health_tips/<tid>/edit", methods=["GET", "POST"])
@role_required("admin")
def health_tip_edit(tid):
    db = get_db()
    fs = gridfs.GridFS(db)
    oid = _oid(tid)
    tip = db.health_tips.find_one({"_id": oid}) or abort(404)
    
    if request.method == "POST":
        f = request.form
        file = request.files.get("image")
        
        update_data = {
            "category": f.get("category", ""),
            "content": {
                "en": {"title": f.get("en_title", ""), "description": f.get("en_text", "")},
                "ta": {"title": f.get("ta_title", ""), "description": f.get("ta_text", "")},
                "hi": {"title": f.get("hi_title", ""), "description": f.get("hi_text", "")}
            },
            "status": f.get("status", "active"),
            "updated_at": datetime.now(timezone.utc)
        }
        
        if file and file.filename:
            # Delete old image from GridFS
            if tip.get("media") and tip["media"].get("file_id"):
                try:
                    fs.delete(tip["media"]["file_id"])
                except Exception:
                    pass
                    
            filename = secure_filename(file.filename)
            file_id = fs.put(file, filename=filename, content_type=file.content_type)
            update_data["media"] = {
                "type": "image",
                "file_id": file_id,
                "filename": filename,
                "mime_type": file.content_type
            }
            
        db.health_tips.update_one({"_id": oid}, {"$set": update_data})
        flash("Health tip updated successfully.", "success")
        return redirect(url_for("admin.health_tips"))
        
    return render_template("admin_health_tip_form.html", tip=tip, edit=True)

@bp.route("/health_tips/<tid>/delete", methods=["POST"])
@role_required("admin")
def health_tip_delete(tid):
    db = get_db()
    fs = gridfs.GridFS(db)
    oid = _oid(tid)
    tip = db.health_tips.find_one({"_id": oid})
    
    if tip:
        if tip.get("media") and tip["media"].get("file_id"):
            try:
                fs.delete(tip["media"]["file_id"])
            except Exception:
                pass
        db.health_tips.delete_one({"_id": oid})
        flash("Health tip deleted.", "success")
        
    return redirect(url_for("admin.health_tips"))
