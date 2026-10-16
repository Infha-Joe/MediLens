import os
from datetime import datetime, timezone
from pymongo import MongoClient, GEOSPHERE, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()
mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = mongo[os.getenv("DB_NAME", "medilens")]

def _now():
    return datetime.now(timezone.utc)

def slugify(text):
    return "".join(c if c.isalnum() else '-' for c in text.lower()).strip('-')

# 1. Indexes
db.users.create_index("email", unique=True)
db.shops.create_index([("location", GEOSPHERE)])
db.shops.create_index("user_id", unique=True)
db.medicines.create_index([("brand", ASCENDING)])
db.medicines.create_index([("salt", ASCENDING)])
db.inventory.create_index([("shop_id", ASCENDING), ("medicine_id", ASCENDING)], unique=True)
db.chat_sessions.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])

# 2. Customers
print("Seeding customers...")
for i in range(1, 6):
    email = f"customer{i}@medilens.test"
    if not db.users.find_one({"email": email}):
        db.users.insert_one({
            "name": f"Test Customer {i}",
            "email": email,
            "password_hash": generate_password_hash("password123"),
            "role": "user",
            "status": "approved",
            "created_at": _now()
        })

# 3. Shops
print("Seeding shops...")
shop_ids = []
shops_data = [
    {"email": "shop1@medilens.test", "shop_name": "MediCare Pharmacy", "lat": 13.0827, "lng": 80.2707},
    {"email": "shop2@medilens.test", "shop_name": "CityCare Pharmacy", "lat": 13.0837, "lng": 80.2717},
    {"email": "shop3@medilens.test", "shop_name": "HealthPlus Pharmacy", "lat": 13.0847, "lng": 80.2727},
]

for idx, s in enumerate(shops_data):
    user = db.users.find_one({"email": s["email"]})
    if not user:
        uid = db.users.insert_one({
            "name": f"Shop Owner {idx+1}",
            "email": s["email"],
            "password_hash": generate_password_hash("password123"),
            "role": "shop",
            "status": "approved",
            "created_at": _now()
        }).inserted_id
    else:
        uid = user["_id"]
        # Ensure status is approved for testing
        db.users.update_one({"_id": uid}, {"$set": {"status": "approved"}})
        
    shop = db.shops.find_one({"user_id": uid})
    if not shop:
        sid = db.shops.insert_one({
            "name": s["shop_name"],
            "address": f"Test Street {idx+1}",
            "license_no": f"LIC{idx+1}2345",
            "phone": "9999999999",
            "hours": "08:00-22:00",
            "delivery": True,
            "location": {"type": "Point", "coordinates": [s["lng"], s["lat"]]},
            "user_id": uid,
            "created_at": _now()
        }).inserted_id
        shop_ids.append(sid)
    else:
        shop_ids.append(shop["_id"])

# 4. Medicines
print("Seeding medicines...")
medicines_data = [
    {"brand": "Dolo", "salt": "Paracetamol", "strength": "650mg", "mrp": 30.0, "uses": "Fever, mild to moderate pain", "side_effects": "Nausea, stomach upset", "warnings": "Avoid alcohol", "rx_required": False},
    {"brand": "Calpol", "salt": "Paracetamol", "strength": "500mg", "mrp": 15.0, "uses": "Fever, pain relief", "side_effects": "Rarely skin rash", "warnings": "Do not overdose", "rx_required": False},
    {"brand": "Brufen", "salt": "Ibuprofen", "strength": "400mg", "mrp": 40.0, "uses": "Pain relief, inflammation", "side_effects": "Heartburn, dizziness", "warnings": "Take with food", "rx_required": False},
    {"brand": "Cetzine", "salt": "Cetirizine", "strength": "10mg", "mrp": 18.0, "uses": "Allergies, runny nose", "side_effects": "Sleepiness, dry mouth", "warnings": "May cause drowsiness", "rx_required": False},
    {"brand": "Azee", "salt": "Azithromycin", "strength": "500mg", "mrp": 120.0, "uses": "Bacterial infections", "side_effects": "Diarrhea, nausea", "warnings": "Complete the full course", "rx_required": True},
    {"brand": "Mox", "salt": "Amoxicillin", "strength": "500mg", "mrp": 80.0, "uses": "Bacterial infections", "side_effects": "Skin rash, stomach upset", "warnings": "Complete the full course", "rx_required": True},
    {"brand": "Omez", "salt": "Omeprazole", "strength": "20mg", "mrp": 55.0, "uses": "Acidity, heartburn", "side_effects": "Headache, nausea", "warnings": "Take before breakfast", "rx_required": False},
    {"brand": "Pan", "salt": "Pantoprazole", "strength": "40mg", "mrp": 110.0, "uses": "Acid reflux, ulcers", "side_effects": "Headache, diarrhea", "warnings": "Take before food", "rx_required": False},
    {"brand": "Electral", "salt": "ORS", "strength": "21g", "mrp": 20.0, "uses": "Dehydration", "side_effects": "None common", "warnings": "Use clean water", "rx_required": False},
    {"brand": "Gelusil", "salt": "Antacid", "strength": "200ml", "mrp": 105.0, "uses": "Acidity, gas", "side_effects": "Constipation", "warnings": "Shake well before use", "rx_required": False},
    {"brand": "Benadryl", "salt": "Cough Syrup", "strength": "150ml", "mrp": 125.0, "uses": "Cough, allergy", "side_effects": "Sleepiness", "warnings": "Do not drive after taking", "rx_required": False},
    {"brand": "Supradyn", "salt": "Multivitamin", "strength": "15 tablets", "mrp": 50.0, "uses": "Nutritional deficiency", "side_effects": "Mild stomach upset", "warnings": "Do not exceed daily dose", "rx_required": False},
    {"brand": "Avil", "salt": "Pheniramine", "strength": "25mg", "mrp": 10.0, "uses": "Allergies", "side_effects": "Drowsiness", "warnings": "May cause severe sleepiness", "rx_required": False},
    {"brand": "Augmentin", "salt": "Amoxicillin + Clavulanic Acid", "strength": "625mg", "mrp": 200.0, "uses": "Bacterial infections", "side_effects": "Diarrhea", "warnings": "Complete the course", "rx_required": True},
    {"brand": "Vicks Action 500", "salt": "Paracetamol + Phenylephrine", "strength": "1 tablet", "mrp": 45.0, "uses": "Cold, headache", "side_effects": "Restlessness", "warnings": "Avoid if you have high blood pressure", "rx_required": False},
]

med_ids = []
for m in medicines_data:
    m["image"] = f"images/medicines/{slugify(m['brand'])}.jpg"
    med = db.medicines.find_one({"brand": m["brand"], "salt": m["salt"]})
    if not med:
        res = db.medicines.insert_one(m)
        med_ids.append(res.inserted_id)
    else:
        # Update existing record to have the image field
        db.medicines.update_one({"_id": med["_id"]}, {"$set": {"image": m["image"]}})
        med_ids.append(med["_id"])

# 5. Inventory
print("Seeding inventory...")
import random
random.seed(42)

for i, sid in enumerate(shop_ids):
    # MediCare Pharmacy gets first 10, CityCare gets middle 10, HealthPlus gets last 10
    start_idx = i * 2
    end_idx = start_idx + 10
    shop_meds = med_ids[start_idx:end_idx]
    
    for mid in shop_meds:
        inv = db.inventory.find_one({"shop_id": sid, "medicine_id": mid})
        if not inv:
            med_info = db.medicines.find_one({"_id": mid})
            mrp = med_info["mrp"]
            
            # Create variations in price and stock
            # Price: between MRP-15% and MRP
            price = round(mrp * random.uniform(0.85, 1.0), 2)
            
            # Make sure we have at least one paracetamol under 50
            if med_info["brand"] == "Dolo" and price > 50:
                price = 28.0
                
            # Stock: mostly in stock, some out of stock
            qty = random.choice([0, 0, 10, 20, 30, 50, 100])
            
            db.inventory.insert_one({
                "shop_id": sid,
                "medicine_id": mid,
                "price": price,
                "qty": qty
            })
            
print("Seed completed!")
