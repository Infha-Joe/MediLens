import os
import re

user_py_path = r"d:\flask_Mongo\medilens_final\medilens\user.py"
shops_html_path = r"d:\flask_Mongo\medilens_final\medilens\templates\shops.html"

# Rewrite shops route and shops_data route
user_code = ""
with open(user_py_path, "r", encoding="utf-8") as f:
    user_code = f.read()

# Replace shops and shops_data completely
shops_code = """
@bp.route("/shops")
@role_required("user")
def shops():
    db = get_db()
    med = db.medicines.find_one({"_id": _oid(request.args.get("mid"))}) or abort(404)
    
    # Extract unique cities from shop addresses
    cities = set()
    for shop in db.shops.find({}, {"address": 1}):
        addr = shop.get("address", "")
        if "," in addr:
            city = addr.split(",")[-1].strip()
        else:
            city = addr.split(" ")[-1].strip() if addr else "Unknown"
        if city:
            cities.add(city)
            
    cities = sorted(list(cities))
    return render_template("shops.html", med=med, cities=cities)


@bp.route("/shops/data")
@role_required("user")
def shops_data():
    db = get_db()
    a = request.args
    mid = _oid(a.get("mid"))
    
    now = datetime.now(ZoneInfo(current_app.config["TIMEZONE"]))
    rows = []
    
    city_filter = a.get("city", "")
    shop_query = {"status": "approved"}
    
    # MongoDB query for City filtering using regex on address
    if city_filter and city_filter != "All Cities":
        shop_query["address"] = {"$regex": city_filter, "$options": "i"}
        
    shops = db.shops.find(shop_query)
    
    for s in shops:
        inv = db.inventory.find_one({"shop_id": s["_id"], "medicine_id": mid, "qty": {"$gt": 0}})
        owner = db.users.find_one({"_id": s["user_id"]})
        if not inv or not owner or owner["status"] != "approved":
            continue
            
        if a.get("delivery") == "1" and not s.get("delivery"):
            continue
            
        opn = is_open(s.get("hours"), now)
        if a.get("open_now") == "1" and opn is False:
            continue
            
        rows.append({
            "id": str(s["_id"]),
            "name": s["name"],
            "address": s["address"],
            "phone": s.get("phone", ""),
            "hours": s.get("hours", ""),
            "delivery": bool(s.get("delivery")),
            "open": opn,
            "price": inv["price"],
            "qty": inv["qty"]
        })
        
    # Sort by price primarily since distance is removed
    rows.sort(key=lambda r: r["price"])
    return jsonify(shops=rows)
"""

# Find and replace the entire shops and shops_data endpoints in user.py
new_user_code = re.sub(
    r'@bp\.route\("/shops"\).*?return jsonify\(shops=rows\)',
    shops_code.strip(),
    user_code,
    flags=re.DOTALL
)

with open(user_py_path, "w", encoding="utf-8") as f:
    f.write(new_user_code)


shops_html_content = """{% extends "base.html" %}
{% block title %}Find Pharmacies · MediLens{% endblock %}
{% block content %}
<div class="mb-6 flex justify-between items-end flex-wrap gap-4">
  <div>
    <h1 class="text-2xl font-bold mb-2">Find Pharmacies</h1>
    <p class="text-muted m-0">Searching availability for <strong class="text-deep">{{ med.brand }} {{ med.strength }}</strong></p>
  </div>
</div>

<div class="card mb-8">
  <div class="flex items-center gap-4 flex-wrap">
    <div class="form-group mb-0" style="flex: 1; min-width: 250px;">
      <label for="city" class="font-bold text-sm">City</label>
      <select id="city" class="w-full">
        <option value="All Cities">All Cities</option>
        {% for city in cities %}
        <option value="{{ city }}">{{ city }}</option>
        {% endfor %}
      </select>
    </div>
    
    <div class="flex items-center gap-4 pt-6">
      <label class="checkbox-label font-bold text-sm"><input type="checkbox" id="delivery"> Home Delivery</label>
      <label class="checkbox-label font-bold text-sm"><input type="checkbox" id="open"> Open Now</label>
    </div>
  </div>
</div>

<div id="status" class="toast info" style="display:none; margin-bottom:1rem;"><i data-lucide="info"></i> <span>Searching...</span></div>

<div class="grid-3" id="results">
  <!-- Results populate here -->
</div>

<script>
(()=>{
const MID="{{ med._id }}", DATA="{{ url_for('user.shops_data') }}";
const $ = id => document.getElementById(id);
const stat = document.querySelector('#status span'), statBox = $('status');
const el = (t, cls, html) => { const e = document.createElement(t); if(cls) e.className=cls; if(html) e.innerHTML=html; return e; };

function msg(text, type='info') {
  statBox.style.display='flex';
  statBox.className='toast '+type;
  statBox.style.position='static'; statBox.style.animation='none'; statBox.style.marginBottom='1rem';
  stat.textContent=text;
  lucide.createIcons();
}

function load() {
  const city = $('city').value;
  const delivery = $('delivery').checked ? 1 : 0;
  const open_now = $('open').checked ? 1 : 0;
  
  const q = new URLSearchParams({mid: MID, city: city, delivery: delivery, open_now: open_now});
  msg('Loading pharmacies...','info');
  
  fetch(DATA+'?'+q).then(r=>r.json()).then(d=>{
    $('results').innerHTML='';
    
    if(d.error){ msg(d.error,'error'); return; }
    
    if(d.shops.length === 0) {
      msg('No pharmacies found for this city.','warning');
      return;
    }
    
    statBox.style.display = 'none'; // Hide message on success
    
    d.shops.forEach(s => {
      const c = el('div', 'card flex-col justify-between hover:shadow-md', '');
      
      let html = `<div class="mb-4">
        <div class="flex justify-between items-start mb-2">
          <h4 class="font-bold m-0 text-lg">${s.name}</h4>
          <span class="badge badge-primary font-bold">₹${s.price}</span>
        </div>
        <div class="text-xs text-muted mb-3 flex items-center gap-1"><i data-lucide="map-pin" style="width:14px"></i> ${s.address}</div>
        `;
        
      let state = s.open === true ? '<span class="text-success font-bold">Open</span>' : s.open === false ? '<span class="text-danger font-bold">Closed</span>' : '';
      let del = s.delivery ? '<span class="badge badge-success" style="font-size:0.6rem">Delivers</span>' : '';
      
      html += `<div class="text-xs mt-1 flex gap-2 items-center flex-wrap">${state} &middot; <span class="font-bold text-deep">${s.qty} in stock</span> ${del}</div>`;
      html += `</div>`;
      
      // Removed Order button entirely per instructions
      c.innerHTML = html;
      $('results').appendChild(c);
    });
    lucide.createIcons();
  }).catch(()=>{ msg('Could not load shops. Check your connection.','error'); });
}

$('city').addEventListener('change', load);
$('delivery').addEventListener('change', load);
$('open').addEventListener('change', load);

// Initial load
load();
})();
</script>
{% endblock %}
"""

with open(shops_html_path, "w", encoding="utf-8") as f:
    f.write(shops_html_content)

print("Rewrote user.py shops endpoints and shops.html successfully.")
