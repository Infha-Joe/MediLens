"""Sample data for testing: python seed_medicines.py
Prices and Rx flags are SAMPLE values. Verify before real use (admin tools arrive in batch 3)."""
from app import create_app
from db import get_db

def slugify(text):
    return "".join(c if c.isalnum() else '-' for c in text.lower()).strip('-')

INFO = {  # salt: (uses, side effects, warnings, prescription required)
    "paracetamol": ("Relieves mild to moderate pain and lowers fever.",
                    "Rare at normal doses; nausea or rash in some people.",
                    "Too much paracetamol can seriously damage the liver. Check other medicines you take for hidden paracetamol.", False),
    "ibuprofen": ("Relieves pain, inflammation, and fever, such as headache, toothache, and muscle pain.",
                  "Stomach upset, heartburn, dizziness.",
                  "Take with food. Ask a doctor first if you have stomach ulcers, kidney problems, or are pregnant.", False),
    "cetirizine": ("Relieves allergy symptoms such as sneezing, runny nose, itchy eyes, and hives.",
                   "Drowsiness, dry mouth.", "May cause drowsiness. Take care when driving.", False),
    "pantoprazole": ("Reduces stomach acid for acidity, heartburn, and acid reflux.",
                     "Headache, diarrhoea, gas.", "Long-term use should be supervised by a doctor.", True),
    "omeprazole": ("Reduces stomach acid for acidity, heartburn, and acid reflux.",
                   "Headache, nausea, stomach pain.", "Long-term use should be supervised by a doctor.", True),
    "amoxicillin": ("Antibiotic for bacterial infections such as ear, throat, chest, and urinary infections.",
                    "Diarrhoea, nausea, rash.",
                    "Prescription only. Tell your doctor if you are allergic to penicillin. Finish the course as prescribed.", True),
    "azithromycin": ("Antibiotic for certain bacterial infections of the chest, throat, skin, and ears.",
                     "Nausea, loose stools, stomach pain.", "Prescription only. Take exactly as prescribed.", True),
    "metformin": ("Helps control blood sugar in type 2 diabetes.",
                  "Nausea, diarrhoea, metallic taste.", "Prescription only. Take only as directed by a doctor.", True),
}
BRANDS = [
    ("Crocin", "paracetamol", "500 mg", 20), ("Calpol", "paracetamol", "500 mg", 16),
    ("Paracip", "paracetamol", "500 mg", 14), ("Dolo", "paracetamol", "650 mg", 30),
    ("Pacimol", "paracetamol", "650 mg", 26), ("Brufen", "ibuprofen", "400 mg", 24),
    ("Ibugesic", "ibuprofen", "400 mg", 18), ("Cetzine", "cetirizine", "10 mg", 22),
    ("Okacet", "cetirizine", "10 mg", 15), ("Alerid", "cetirizine", "10 mg", 19),
    ("Pantocid", "pantoprazole", "40 mg", 150), ("Pantop", "pantoprazole", "40 mg", 120),
    ("Omez", "omeprazole", "20 mg", 65), ("Ocid", "omeprazole", "20 mg", 50),
    ("Novamox", "amoxicillin", "500 mg", 95), ("Mox", "amoxicillin", "500 mg", 85),
    ("Azithral", "azithromycin", "500 mg", 120), ("Azee", "azithromycin", "500 mg", 110),
    ("Glycomet", "metformin", "500 mg", 28), ("Obimet", "metformin", "500 mg", 22),
]

with create_app().app_context():
    db = get_db()
    for brand, salt, strength, mrp in BRANDS:
        uses, side, warn, rx = INFO[salt]
        img_path = f"images/medicines/{slugify(brand)}.jpg"
        db.medicines.update_one({"brand": brand, "strength": strength}, {"$set": {
            "brand": brand, "salt": salt, "strength": strength, "mrp": mrp,
            "uses": uses, "side_effects": side, "warnings": warn, "rx_required": rx, "image": img_path}}, upsert=True)
    print("Medicines in database:", db.medicines.count_documents({}))
