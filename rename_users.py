import re
from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017')['medilens']

def get_realistic_email(old_email):
    # Mapping exact prefixes
    prefix = old_email.split('@')[0]
    m = {
        "customer1": "ravi@gmail.com",
        "customer2": "priya@gmail.com",
        "customer3": "arun@gmail.com",
        "customer4": "meena@gmail.com",
        "customer5": "karthik@gmail.com",
        "customer6": "divya@gmail.com",
        "customer7": "suresh@gmail.com",
        "customer8": "anita@gmail.com",
        "customer9": "vijay@gmail.com",
        "customer10": "sneha@gmail.com",
        "shop1": "rameshpharmacy@gmail.com",
        "shop2": "citycarepharmacy@gmail.com",
        "shop3": "healthpluspharmacy@gmail.com",
        "shop4": "chennaimed@gmail.com",
        "shop5": "maduraicare@gmail.com",
    }
    
    # Check if we have a direct map
    if prefix in m:
        return m[prefix]
        
    # If not, generate a generic realistic-looking one
    if prefix.startswith("customer"):
        num = prefix.replace("customer", "")
        names = ["kumar", "lakshmi", "rajesh", "sunita", "mohan"]
        idx = int(num) % len(names) if num.isdigit() else 0
        return f"{names[idx]}{num}@gmail.com"
        
    if prefix.startswith("shop"):
        num = prefix.replace("shop", "")
        names = ["apollo", "medplus", "netmeds", "trust", "care"]
        idx = int(num) % len(names) if num.isdigit() else 0
        return f"{names[idx]}pharmacy{num}@gmail.com"
        
    return old_email


print("Updating database users...")
for u in db.users.find({"role": {"$in": ["user", "shop"]}}):
    old = u["email"]
    new = get_realistic_email(old)
    
    if old != new:
        # Check if new already exists (just in case)
        if db.users.find_one({"email": new}):
            new = f"{new.split('@')[0]}_{old.split('@')[1]}@gmail.com" # Append domain to make it unique
            
        res = db.users.update_one({"_id": u["_id"]}, {"$set": {"email": new}})
        if res.modified_count > 0:
            print(f"Updated {old} -> {new}")

print("Database update complete.")

# Update templates/login.html
login_path = r"d:\flask_Mongo\medilens_final\medilens\templates\login.html"
try:
    with open(login_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'customer1@.*?(<|")|customer1', 'ravi@gmail.com', content)
    content = re.sub(r'shop1@.*?(<|")|shop1', 'rameshpharmacy@gmail.com', content)
    with open(login_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated login.html")
except Exception as e:
    print(f"Error updating login.html: {e}")
