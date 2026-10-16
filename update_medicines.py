import os
import shutil
import glob
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont
import hashlib

def slugify(text):
    return "".join(c if c.isalnum() else '-' for c in text.lower()).strip('-')

def generate_box_image(brand, strength, salt, form, out_path):
    img = Image.new('RGB', (800, 800), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)
    
    # Generate a deterministic pastel color based on brand
    h = int(hashlib.md5(brand.encode()).hexdigest(), 16)
    r = 200 + (h % 55)
    g = 200 + ((h >> 8) % 55)
    b = 200 + ((h >> 16) % 55)
    
    # Draw a colored box in the center to look like a package
    draw.rectangle([100, 150, 700, 650], fill=(r, g, b), outline=(200, 200, 200), width=3)
    
    # Draw white label area
    draw.rectangle([150, 200, 650, 500], fill=(255, 255, 255))
    
    # Text
    try:
        # Try to use a default font
        font_large = ImageFont.truetype("arial.ttf", 60)
        font_medium = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 25)
    except:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    draw.text((180, 230), brand[:20], fill=(30, 41, 59), font=font_large)
    if strength:
        draw.text((180, 310), strength, fill=(71, 85, 105), font=font_medium)
    if salt:
        draw.text((180, 400), salt[:40], fill=(100, 116, 139), font=font_small)
        
    form_text = "SYRUP" if "syrup" in str(form).lower() else ("DROPS" if "drop" in str(form).lower() else "TABLETS / CAPSULES")
    draw.text((180, 550), form_text, fill=(50, 50, 50), font=font_medium)
    
    img.save(out_path)


db = MongoClient('mongodb://localhost:27017/')['medilens']
meds = list(db.medicines.find())

static_dir = r"d:\flask_Mongo\medilens_final\medilens\static\images\medicines"
os.makedirs(static_dir, exist_ok=True)

brain_dir = r"C:\Users\ADMIN\.gemini\antigravity-ide\brain\a68ee0af-03c8-489b-9560-38fb5935ec38"

for med in meds:
    brand = med['brand']
    slug = slugify(brand)
    filename = f"{slug}.jpg"
    out_path = os.path.join(static_dir, filename)
    
    # Check if we have an AI generated image
    ai_img = glob.glob(os.path.join(brain_dir, f"{slug}_*.jpg"))
    if ai_img:
        shutil.copy(ai_img[0], out_path)
        print(f"Copied AI image for {brand}")
    else:
        generate_box_image(brand, med.get('strength', ''), med.get('salt', ''), med.get('brand', '') + med.get('salt', ''), out_path)
        print(f"Generated PIL image for {brand}")
        
    # Update DB
    db.medicines.update_one({'_id': med['_id']}, {'$set': {'image': f"images/medicines/{filename}"}})
    
print(f"Updated {len(meds)} medicines.")
