from pymongo import MongoClient, ASCENDING, DESCENDING, GEOSPHERE

_db = None


def init_db(app):
    global _db
    client = MongoClient(app.config["MONGO_URI"])
    _db = client[app.config["DB_NAME"]]
    _db.users.create_index("email", unique=True)
    _db.shops.create_index([("location", GEOSPHERE)])
    _db.shops.create_index("user_id", unique=True)
    _db.medicines.create_index([("brand", ASCENDING)])
    _db.medicines.create_index([("salt", ASCENDING)])
    _db.inventory.create_index(
        [("shop_id", ASCENDING), ("medicine_id", ASCENDING)], unique=True
    )
    _db.search_history.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])


def get_db():
    return _db
