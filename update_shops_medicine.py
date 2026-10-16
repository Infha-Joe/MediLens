import re
user_py_path = r"d:\flask_Mongo\medilens_final\medilens\user.py"

# Rewrite shops route to include all_medicines
with open(user_py_path, "r", encoding="utf-8") as f:
    user_code = f.read()

shops_code = """@bp.route("/shops")
@role_required("user")
def shops():
    db = get_db()
    mid = request.args.get("mid")
    med = db.medicines.find_one({"_id": _oid(mid)}) if mid else None
    
    # Get all medicines for dropdown (sorted by brand)
    all_medicines = list(db.medicines.find({}, {"brand": 1, "strength": 1, "salt": 1}).sort("brand", 1))
    
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
    return render_template("shops.html", med=med, cities=cities, all_medicines=all_medicines)"""

new_user_code = re.sub(
    r'@bp\.route\("/shops"\).*?return render_template\("shops\.html", med=med, cities=cities\)',
    shops_code.strip(),
    user_code,
    flags=re.DOTALL
)

with open(user_py_path, "w", encoding="utf-8") as f:
    f.write(new_user_code)


# Update shops.html to include Medicine selector
shops_html_path = r"d:\flask_Mongo\medilens_final\medilens\templates\shops.html"
with open(shops_html_path, "r", encoding="utf-8") as f:
    shops_html = f.read()

new_header = """<div class="mb-6 flex justify-between items-end flex-wrap gap-4">
  <div>
    <h1 class="text-2xl font-bold mb-2">Find Pharmacies</h1>
    <p class="text-muted m-0">Check availability in local pharmacies.</p>
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
    
    <div class="form-group mb-0" style="flex: 1; min-width: 250px;">
      <label for="mid" class="font-bold text-sm">Medicine</label>
      <select id="mid" class="w-full">
        <option value="">Select a Medicine...</option>
        {% for m in all_medicines %}
        <option value="{{ m._id }}" {% if med and med._id == m._id %}selected{% endif %}>{{ m.brand }} {{ m.strength }}</option>
        {% endfor %}
      </select>
    </div>
    
    <div class="flex items-center gap-4 pt-6">
      <label class="checkbox-label font-bold text-sm"><input type="checkbox" id="delivery"> Home Delivery</label>
      <label class="checkbox-label font-bold text-sm"><input type="checkbox" id="open"> Open Now</label>
    </div>
  </div>
</div>"""

shops_html = re.sub(
    r'<div class="mb-6 flex justify-between items-end flex-wrap gap-4">.*?</div>\s*</div>',
    new_header,
    shops_html,
    flags=re.DOTALL
)

# Update javascript
js_update = """function load() {
  const city = $('city').value;
  const mid = $('mid').value;
  const delivery = $('delivery').checked ? 1 : 0;
  const open_now = $('open').checked ? 1 : 0;
  
  if (!mid) {
      $('results').innerHTML = '<div class="card text-center text-muted" style="grid-column: 1/-1;">Please select a medicine to see availability.</div>';
      return;
  }
  
  const q = new URLSearchParams({mid: mid, city: city, delivery: delivery, open_now: open_now});"""

shops_html = re.sub(
    r'function load\(\) \{.*?const q = new URLSearchParams\(\{mid: MID, city: city, delivery: delivery, open_now: open_now\}\);',
    js_update,
    shops_html,
    flags=re.DOTALL
)

# Remove the MID constant definition since we pull it dynamically from the select box now
shops_html = re.sub(r'const MID="{{ med._id }}", ', 'const ', shops_html)

# Add event listener for mid
shops_html = shops_html.replace("$('city').addEventListener('change', load);", "$('city').addEventListener('change', load);\n$('mid').addEventListener('change', load);")

with open(shops_html_path, "w", encoding="utf-8") as f:
    f.write(shops_html)

print("Added Medicine dropdown to shops finder.")
