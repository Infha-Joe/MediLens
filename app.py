import os
import secrets

from flask import Flask, abort, redirect, render_template, request, session, url_for

from auth import HOME, bp as auth_bp
from chat import LANGS, bp as chat_bp
from config import Config
from db import init_db
from admin import bp as admin_bp
from shop import bp as shop_bp
from user import bp as user_bp

TRANSLATIONS = {
    "en": {
        "Dashboard": "Dashboard",
        "Search Medicines": "Search Medicines",
        "Orders": "Orders",
        "History": "History",
        "MediLens AI": "MediLens AI",
        "New Chat": "New Chat",
        "Language": "Language",
        "Log out": "Log out",
        "Loading...": "Loading...",
        "No recent chats": "No recent chats",
        "Unable to load conversations": "Unable to load conversations",
        "Medicine not found": "Medicine not found",
        "No results found": "No results found",
        "View Full Details": "View Full Details",
        "Find Nearby": "Find Nearby",
        "Prescription Required": "Prescription Required",
        "OTC Available": "OTC Available",
        "Recent Orders": "Recent Orders",
        "Recent Medicines": "Recent Medicines",
        "Pharmacies": "Pharmacies",
        "Medicines": "Medicines",
        "Customers": "Customers",
    },
    "ta": {
        "Dashboard": "முகப்பு",
        "Search Medicines": "மருந்துகளை தேடு",
        "Orders": "ஆர்டர்கள்",
        "History": "வரலாறு",
        "MediLens AI": "மெடிலென்ஸ் ஏஐ",
        "New Chat": "புதிய உரையாடல்",
        "Language": "மொழி",
        "Log out": "வெளியேறு",
        "Loading...": "ஏற்றுகிறது...",
        "No recent chats": "சமீபத்திய உரையாடல்கள் இல்லை",
        "Unable to load conversations": "உரையாடல்களை ஏற்ற முடியவில்லை",
        "Medicine not found": "மருந்து கிடைக்கவில்லை",
        "No results found": "முடிவுகள் கிடைக்கவில்லை",
        "View Full Details": "முழு விவரங்களைப் பார்",
        "Find Nearby": "அருகில் தேடு",
        "Prescription Required": "பரிந்துரை சீட்டு தேவை",
        "OTC Available": "சீட்டு இல்லாமல் கிடைக்கும்",
        "Recent Orders": "சமீபத்திய ஆர்டர்கள்",
        "Recent Medicines": "சமீபத்திய மருந்துகள்",
        "Pharmacies": "மருந்தகங்கள்",
        "Medicines": "மருந்துகள்",
        "Customers": "வாடிக்கையாளர்கள்",
    },
    "hi": {
        "Dashboard": "डैशबोर्ड",
        "Search Medicines": "दवाइयां खोजें",
        "Orders": "ऑर्डर",
        "History": "इतिहास",
        "MediLens AI": "मेडीलेंस एआई",
        "New Chat": "नया चैट",
        "Language": "भाषा",
        "Log out": "लॉग आउट",
        "Loading...": "लोड हो रहा है...",
        "No recent chats": "कोई हालिया चैट नहीं",
        "Unable to load conversations": "चैट लोड करने में असमर्थ",
        "Medicine not found": "दवा नहीं मिली",
        "No results found": "कोई परिणाम नहीं मिला",
        "View Full Details": "पूर्ण विवरण देखें",
        "Find Nearby": "आस-पास खोजें",
        "Prescription Required": "पर्चे की आवश्यकता है",
        "OTC Available": "पर्चे के बिना उपलब्ध",
        "Recent Orders": "हाल के ऑर्डर",
        "Recent Medicines": "हाल की दवाएं",
        "Pharmacies": "फार्मेसियों",
        "Medicines": "दवाइयां",
        "Customers": "ग्राहक",
    }
}

# Health tips are now stored in MongoDB

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app)
    for bp in (auth_bp, user_bp, shop_bp, admin_bp, chat_bp):
        app.register_blueprint(bp)

    @app.before_request
    def csrf_protect():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        if request.method == "POST":
            sent = request.form.get("csrf") or request.headers.get("X-CSRF") or ""
            if not secrets.compare_digest(sent, session["csrf"]):
                abort(400)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def friendly_error(e):
        msg = {400: "That request couldn't be verified. Go back, refresh the page, and try again.",
               404: "We couldn't find that page.",
               413: "That file is too large. Photos must be under 5 MB."}[e.code]
        return render_template("error.html", msg=msg), e.code

    @app.context_processor
    def inject_langs():
        def _(text):   # used to send common variables to templates
            lang = session.get("lang", "en")
            if lang not in TRANSLATIONS:
                lang = "en"
            return TRANSLATIONS[lang].get(text, text)
            
        import datetime
        from db import get_db
        db = get_db()
        active_tips = list(db.health_tips.find({"status": "active"}))
        lang = session.get("lang", "en")
        if lang not in ["en", "ta", "hi"]: lang = "en"
        
        all_tips = []
        for raw_tip in active_tips:
            content = raw_tip.get("content", {}).get(lang, {})
            if not content.get("title"):
                content = raw_tip.get("content", {}).get("en", {})
            media = raw_tip.get("media")
            image_url = ""
            if media and media.get("file_id"):
                image_url = url_for("health_tip_media", file_id=str(media["file_id"]))
            
            all_tips.append({
                "category": raw_tip.get("category", ""),
                "image": image_url,
                "title": content.get("title", ""),
                "text": content.get("description", "")
            })
            
        return {"LANGS": LANGS, "csrf": session.get("csrf", ""), "_": _, "all_tips": all_tips}

    @app.route("/")
    def index():
        role = session.get("role")
        return redirect(url_for(HOME[role]) if role else url_for("auth.login"))

    @app.route("/api/health-tips/media/<file_id>")
    def health_tip_media(file_id):
        import gridfs
        from bson import ObjectId, errors
        from flask import send_file
        from io import BytesIO
        from db import get_db
        db = get_db()
        fs = gridfs.GridFS(db)
        try:
            file_data = fs.get(ObjectId(file_id))
            return send_file(BytesIO(file_data.read()), mimetype=file_data.content_type)
        except (errors.InvalidId, gridfs.errors.NoFile):
            abort(404)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
