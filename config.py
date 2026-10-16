import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "medilens")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    CHAT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
    SESSION_COOKIE_SAMESITE = "Lax"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB per image
