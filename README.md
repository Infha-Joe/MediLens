# MediLens (Flask + MongoDB)

## Run
1. Install Python 3.10+ and MongoDB (local or Atlas).
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and edit values.
4. Install the Tesseract OCR program (needed for photo scan): Windows installer from the UB Mannheim build, or `sudo apt install tesseract-ocr`
5. `python seed_admin.py` (admin login) then `python seed_medicines.py` (20 sample medicines; prices and Rx flags are sample values, verify them)
6. `python app.py` then open http://127.0.0.1:5000

## AI chatbot key
Paste your key into `.env` as `GROQ_API_KEY=...` (used from batch 4).

## Roles
- Customer: register and log in right away.
- Shop: registers with license and location, then waits for admin approval.
- Admin: seeded with `seed_admin.py`; approves or blocks shops at /admin/shops.

## Build status
Batch 1 done: setup, 3-role login, shop approval.
Batch 2 done: photo scan (OCR), name search, medicine details, same-salt alternatives, search history.
Batch 3 done: shop stock/price management, shop orders and profile, admin medicine database and user control, customer orders with prescription upload for Rx medicines.
Batch 4 done: AI chatbot per medicine (grounded in your data, with safety rules), voice input and read-aloud, English/Tamil/Hindi answers and AI-translated medicine info (cached). Without an API key the chatbot gives basic answers from stored data.
Batch 5 done: nearest-shop finder with map (Leaflet + OpenStreetMap), radius slider, sort by distance or price, delivery and open-now filters, CSRF protection, friendly error pages. 3 shop and admin modules, 5 location search and polish.

## Before showing it to others
- Set a long random SECRET_KEY and change ADMIN_PASSWORD in .env.
- Run behind HTTPS (voice input and location need it outside localhost).
- Check every medicine's MRP, Rx flag, and text with a pharmacist; the seed data is sample only.
- Shop hours should look like `9:00 AM - 9:00 PM` or `24 hours` for the Open now filter to work.
- The area search uses the free OpenStreetMap Nominatim service (light use only).
