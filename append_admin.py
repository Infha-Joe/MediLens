import datetime
import os
import gridfs
import re
from bson import ObjectId
from werkzeug.utils import secure_filename

# The append content for admin.py   normal crud  health tipsku
admin_health_tips_code = """
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
"""

with open(r"d:\flask_Mongo\medilens_final\medilens\admin.py", "a", encoding="utf-8") as f:
    f.write(admin_health_tips_code)

print("Admin routes appended successfully.")
