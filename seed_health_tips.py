import os
from datetime import datetime, timezone
import gridfs
from bson import ObjectId
from app import create_app
from db import get_db

HEALTH_TIPS = [
    {
        "category": "Hydration",
        "image": "hydration.jpg",
        "en": {"title": "Stay Hydrated", "text": "Drinking enough water throughout the day helps support normal body functions and can help prevent dehydration."},
        "ta": {"title": "நீர்ச்சத்தை போதுமான அளவு பராமரிக்கவும்", "text": "நாள் முழுவதும் போதுமான தண்ணீர் குடிப்பது உடலின் இயல்பான செயல்பாடுகளை ஆதரிக்கிறது."},
        "hi": {"title": "पर्याप्त पानी पिएं", "text": "दिन भर पर्याप्त पानी पीने से शरीर के सामान्य कार्यों में मदद मिलती है।"}
    },
    {
        "category": "Nutrition",
        "image": "nutrition.jpg",
        "en": {"title": "Eat Balanced Meals", "text": "Include a variety of fruits and vegetables in your daily diet to get essential vitamins and minerals."},
        "ta": {"title": "சமச்சீரான உணவு", "text": "அத்தியாவசிய வைட்டமின்களைப் பெற உங்கள் உணவில் பல்வேறு பழங்கள் மற்றும் காய்கறிகளைச் சேர்க்கவும்."},
        "hi": {"title": "संतुलित आहार लें", "text": "विटामिन प्राप्त करने के लिए अपने दैनिक आहार में विभिन्न प्रकार के फल और सब्जियां शामिल करें।"}
    },
    {
        "category": "Sleep",
        "image": "sleep.jpg",
        "en": {"title": "Get Enough Rest", "text": "Aim for 7-9 hours of quality sleep each night to help your body recover and maintain good mental health."},
        "ta": {"title": "போதுமான ஓய்வு எடுக்கவும்", "text": "உங்கள் உடல் மீட்கவும் நல்ல மன ஆரோக்கியத்தை பராமரிக்கவும் 7-9 மணிநேர தூக்கத்தை இலக்காகக் கொள்ளுங்கள்."},
        "hi": {"title": "पर्याप्त आराम करें", "text": "अपने शरीर को ठीक होने में मदद करने के लिए हर रात 7-9 घंटे की अच्छी नींद का लक्ष्य रखें।"}
    },
    {
        "category": "Hygiene",
        "image": "hygiene.jpg",
        "en": {"title": "Wash Your Hands", "text": "Regular hand washing with soap and water is one of the best ways to remove germs and avoid getting sick."},
        "ta": {"title": "கைகளை கழுவவும்", "text": "கிருமிகளை அகற்றுவதற்கும் நோய்வாய்ப்படுவதைத் தவிர்ப்பதற்கும் கைகளை கழுவுவது சிறந்த வழிகளில் ஒன்றாகும்."},
        "hi": {"title": "अपने हाथ धोएं", "text": "साबुन से नियमित रूप से हाथ धोना कीटाणुओं को दूर करने और बीमार होने से बचने के सर्वोत्तम तरीकों में से एक है।"}
    },
    {
        "category": "Medicine Safety",
        "image": "med_safety.jpg",
        "en": {"title": "Check Expiry Dates", "text": "Always check the expiry date before taking any medicine. Do not consume expired medications."},
        "ta": {"title": "காலாவதி தேதியை சரிபார்க்கவும்", "text": "எந்தவொரு மருந்தையும் உட்கொள்வதற்கு முன் காலாவதி தேதியை எப்போதும் சரிபார்க்கவும்."},
        "hi": {"title": "समाप्ति तिथि जांचें", "text": "कोई भी दवा लेने से पहले हमेशा समाप्ति तिथि की जांच करें।"}
    },
    {
        "category": "Medicine Safety",
        "image": "med_safety.jpg",
        "en": {"title": "Store Medicines Safely", "text": "Keep medicines in a cool, dry place out of reach of children. Avoid storing them in direct sunlight."},
        "ta": {"title": "மருந்துகளை பாதுகாப்பாக சேமிக்கவும்", "text": "மருந்துகளை குளிர்ந்த, வறண்ட இடத்தில், குழந்தைகளுக்கு எட்டாதவாறு வைக்கவும்."},
        "hi": {"title": "दवाओं को सुरक्षित रखें", "text": "दवाओं को बच्चों की पहुंच से दूर ठंडी, सूखी जगह पर रखें।"}
    },
    {
        "category": "Hydration",
        "image": "hydration.jpg",
        "en": {"title": "Limit Sugary Drinks", "text": "Substitute sodas and sugary juices with water or herbal teas to reduce empty calories."},
        "ta": {"title": "சர்க்கரை பானங்களை குறைக்கவும்", "text": "வெற்று கலோரிகளை குறைக்க சர்க்கரை சாறுகளுக்கு பதிலாக தண்ணீர் குடிக்கவும்."},
        "hi": {"title": "मीठे पेय सीमित करें", "text": "कैलोरी कम करने के लिए मीठे जूस की जगह पानी पिएं।"}
    },
    {
        "category": "Physical Activity",
        "image": "nutrition.jpg",
        "en": {"title": "Stay Active", "text": "Try to incorporate at least 30 minutes of moderate physical activity into your daily routine."},
        "ta": {"title": "சுறுசுறுப்பாக இருங்கள்", "text": "உங்கள் தினசரி வழக்கத்தில் குறைந்தது 30 நிமிட மிதமான உடல் செயல்பாடுகளைச் சேர்க்க முயற்சிக்கவும்."},
        "hi": {"title": "सक्रिय रहें", "text": "अपनी दिनचर्या में कम से कम 30 मिनट की शारीरिक गतिविधि शामिल करने का प्रयास करें।"}
    },
    {
        "category": "General Health",
        "image": "sleep.jpg",
        "en": {"title": "Reduce Screen Time", "text": "Limit screen time before bed to improve your sleep quality and reduce eye strain."},
        "ta": {"title": "திரை நேரத்தை குறைக்கவும்", "text": "உங்கள் தூக்கத்தின் தரத்தை மேம்படுத்த தூங்குவதற்கு முன் திரை நேரத்தை கட்டுப்படுத்துங்கள்."},
        "hi": {"title": "स्क्रीन टाइम कम करें", "text": "अपनी नींद की गुणवत्ता में सुधार के लिए सोने से पहले स्क्रीन टाइम सीमित करें।"}
    },
    {
        "category": "Medicine Safety",
        "image": "med_safety.jpg",
        "en": {"title": "Follow Prescriptions", "text": "Always complete the full course of antibiotics prescribed by your doctor, even if you feel better."},
        "ta": {"title": "பரிந்துரைகளை பின்பற்றவும்", "text": "நீங்கள் நன்றாக உணர்ந்தாலும், உங்கள் மருத்துவர் பரிந்துரைத்த மருந்துப் படிப்பை எப்போதும் முடிக்கவும்."},
        "hi": {"title": "पर्चे का पालन करें", "text": "भले ही आप बेहतर महसूस करें, हमेशा अपने डॉक्टर द्वारा निर्धारित दवाओं का पूरा कोर्स पूरा करें।"}
    }
]

app = create_app()
with app.app_context():
    db = get_db()
    fs = gridfs.GridFS(db)
    
    # Optional: Clear existing for idempotency
    db.health_tips.delete_many({})
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(base_dir, "static", "images", "tips")
    
    admin_user = db.users.find_one({"role": "admin"})
    admin_ref = {"user_id": admin_user["_id"], "name": admin_user.get("name", "Admin")} if admin_user else {"user_id": None, "name": "System"}
    
    count = 0
    for tip in HEALTH_TIPS:
        img_path = os.path.join(img_dir, tip["image"])
        file_id = None
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                file_id = fs.put(f, filename=tip["image"], content_type="image/jpeg")
        
        doc = {
            "category": tip["category"],
            "content": {
                "en": {"title": tip["en"]["title"], "description": tip["en"]["text"]},
                "ta": {"title": tip["ta"]["title"], "description": tip["ta"]["text"]},
                "hi": {"title": tip["hi"]["title"], "description": tip["hi"]["text"]}
            },
            "media": {
                "type": "image",
                "file_id": file_id,
                "filename": tip["image"],
                "mime_type": "image/jpeg"
            } if file_id else None,
            "status": "active",
            "created_by": admin_ref,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        db.health_tips.insert_one(doc)
        count += 1
        
    # Indexes
    db.health_tips.create_index("category")
    db.health_tips.create_index("status")
    db.health_tips.create_index("created_at")
    
    print(f"Successfully seeded {count} health tips with GridFS images.")
