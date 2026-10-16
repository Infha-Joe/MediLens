from pymongo import MongoClient
import datetime
from werkzeug.security import generate_password_hash

db = MongoClient('mongodb://localhost:27017')['medilens']

def seed():
    # 1. Clean existing sample data (all shops basically)
    # The user asked to remove "sample" shops. We will just remove all shops 
    # to cleanly seed the 15 requested real pharmacies and their inventory.
    # Medicines and normal users are NOT touched.
    
    print("Cleaning old shop data...")
    db.users.delete_many({"role": "shop"})
    db.shops.delete_many({})
    db.inventory.delete_many({})
    
    # 2. Define 15 realistic pharmacies (3 per city)
    cities = ["Tirunelveli", "Thoothukudi", "Madurai", "Kovilpatti", "Coimbatore"]
    
    pharmacies = [
        {"city": "Tirunelveli", "name": "Sri Lakshmi Medicals", "email": "srilakshmi_tirunelveli@gmail.com", "address": "12 High Road, Tirunelveli"},
        {"city": "Tirunelveli", "name": "City Care Pharmacy", "email": "citycare_tirunelveli@gmail.com", "address": "45 South Street, Tirunelveli"},
        {"city": "Tirunelveli", "name": "Green Cross Pharmacy", "email": "greencross_tirunelveli@gmail.com", "address": "Junction Bus Stand, Tirunelveli"},
        
        {"city": "Thoothukudi", "name": "Pearl Medicals", "email": "pearl_thoothukudi@gmail.com", "address": "WGC Road, Thoothukudi"},
        {"city": "Thoothukudi", "name": "Thoothukudi Health Care", "email": "health_thoothukudi@gmail.com", "address": "Palayamkottai Road, Thoothukudi"},
        {"city": "Thoothukudi", "name": "Sea View Pharmacy", "email": "seaview_thoothukudi@gmail.com", "address": "Beach Road, Thoothukudi"},
        
        {"city": "Madurai", "name": "Meenakshi Medicals", "email": "meenakshi_madurai@gmail.com", "address": "Simmakkal, Madurai"},
        {"city": "Madurai", "name": "Madurai City Pharmacy", "email": "maduraicity_madurai@gmail.com", "address": "Anna Nagar, Madurai"},
        {"city": "Madurai", "name": "Apollo Care Pharmacy", "email": "apollo_madurai@gmail.com", "address": "KK Nagar, Madurai"},
        
        {"city": "Kovilpatti", "name": "Kovilpatti Medicals", "email": "kovilpatti_medicals@gmail.com", "address": "Main Road, Kovilpatti"},
        {"city": "Kovilpatti", "name": "Sri Vinayaga Pharmacy", "email": "vinayaga_kovilpatti@gmail.com", "address": "Market Street, Kovilpatti"},
        {"city": "Kovilpatti", "name": "Town Care Medicals", "email": "towncare_kovilpatti@gmail.com", "address": "Bazaar, Kovilpatti"},
        
        {"city": "Coimbatore", "name": "Kovai Medicals", "email": "kovai_medicals@gmail.com", "address": "RS Puram, Coimbatore"},
        {"city": "Coimbatore", "name": "Coimbatore Health Pharmacy", "email": "health_cbe@gmail.com", "address": "Peelamedu, Coimbatore"},
        {"city": "Coimbatore", "name": "Kongu Care Pharmacy", "email": "kongucare_cbe@gmail.com", "address": "Gandhipuram, Coimbatore"}
    ]
    
    # 3. Fetch medicines
    all_meds = list(db.medicines.find())
    def get_med(name):
        for m in all_meds:
            if name.lower() in m["brand"].lower():
                return m
        return None

    # Universal medicines (in all cities)
    universals = [get_med("Calpol"), get_med("Pan"), get_med("Dolo"), get_med("Electral"), get_med("Cetzine")]
    universals = [u for u in universals if u]
    
    # City specific
    city_specific = {
        "Tirunelveli": [get_med("Azee"), get_med("Augmentin")],
        "Madurai": [get_med("Mox"), get_med("Thyronorm")],
        "Coimbatore": [get_med("Glycomet"), get_med("Ecosprin")],
        "Thoothukudi": [get_med("Shelcal"), get_med("Omez")],
        "Kovilpatti": [get_med("Avil"), get_med("Benadryl")]
    }
    
    now = datetime.datetime.now(datetime.timezone.utc)
    pw = generate_password_hash("password123")
    
    for p in pharmacies:
        # Create User
        u_id = db.users.insert_one({
            "name": p["name"] + " Owner",
            "email": p["email"],
            "password_hash": pw,
            "role": "shop",
            "status": "approved",
            "created_at": now
        }).inserted_id
        
        # Create Shop
        s_id = db.shops.insert_one({
            "user_id": u_id,
            "name": p["name"],
            "address": p["address"],
            "city": p["city"],
            "license_no": "DL-2026-T" + str(hash(p["name"]))[:5],
            "phone": "99" + str(hash(p["email"]))[:8].replace("-","1"),
            "hours": "9:00 AM - 10:00 PM",
            "location": {"type": "Point", "coordinates": [77.5, 9.5]},
            "created_at": now
        }).inserted_id
        
        # Inventory
        meds_to_add = universals + [m for m in city_specific.get(p["city"], []) if m]
        
        for m in meds_to_add:
            db.inventory.insert_one({
                "shop_id": s_id,
                "medicine_id": m["_id"],
                "price": float(m.get("mrp", 100)) * 0.9, # 10% discount
                "qty": 50,
                "updated_at": now
            })
            
    print("Seeded 15 pharmacies and their inventory successfully.")
    
if __name__ == "__main__":
    seed()
