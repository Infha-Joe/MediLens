"""Run once: python seed_admin.py  (reads ADMIN_EMAIL / ADMIN_PASSWORD from .env)"""
import os
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from db import get_db

app = create_app()
email = os.getenv("ADMIN_EMAIL", "admin@medilens.local").lower()
password = os.getenv("ADMIN_PASSWORD", "ChangeMe123")
with app.app_context():
    db = get_db()
    if db.users.find_one({"email": email}):
        print("Admin already exists:", email)
    else:
        db.users.insert_one({"name": "Admin", "email": email, "role": "admin",
                             "status": "approved",
                             "password_hash": generate_password_hash(password),
                             "created_at": datetime.now(timezone.utc)})
        print("Admin created:", email)
