import os
import re

user_py_path = r"d:\flask_Mongo\medilens_final\medilens\user.py"
search_html_path = r"d:\flask_Mongo\medilens_final\medilens\templates\search.html"

# Rewrite search route
with open(user_py_path, "r", encoding="utf-8") as f:
    user_code = f.read()

search_code = """@bp.route("/search")
@role_required("user")
def search():
    q = request.args.get("q", "").strip()
    results = []
    is_random = False
    
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        results = list(get_db().medicines.find({"$or": [{"brand": rx}, {"salt": rx}]}).limit(20))
    else:
        results = list(get_db().medicines.aggregate([{"$sample": {"size": 8}}]))
        is_random = True
        
    return render_template("search.html", q=q, results=results, is_random=is_random)"""

new_user_code = re.sub(
    r'@bp\.route\("/search"\).*?return render_template\("search\.html", q=q, results=results\)',
    search_code.strip(),
    user_code,
    flags=re.DOTALL
)

with open(user_py_path, "w", encoding="utf-8") as f:
    f.write(new_user_code)


search_html_content = """{% extends "base.html" %}
{% block title %}Search Medicines · MediLens{% endblock %}
{% block content %}
<div class="mb-6">
  <h1 class="text-2xl font-bold mb-2">Search Medicines</h1>
  <p class="text-muted m-0">Find medicines and check availability in nearby pharmacies.</p>
</div>

<div class="card mb-8">
  <form method="get" action="{{ url_for('user.search') }}" class="flex gap-2 w-full">
    <div class="flex-1 relative">
      <i data-lucide="search" class="absolute left-3 top-1/2" style="transform: translateY(-50%); color: var(--text-muted); width: 18px"></i>
      <input id="q" name="q" value="{{ q }}" placeholder="Search by brand or salt name (e.g. Paracetamol)..." style="width: 100%; padding-left: 2.5rem; height: 48px; border-radius: var(--radius-md);">
    </div>
    <button type="submit" class="btn" style="height: 48px; padding: 0 2rem;">Search</button>
  </form>
</div>

{% if not q and not is_random %}
  <!-- Empty placeholder just in case -->
{% elif results %}
  {% if not is_random %}
  <div class="mb-4">
    <h3 class="text-lg font-bold">Search results for "{{ q }}"</h3>
    <p class="text-sm text-muted">Found {{ results|length }} matching medicines.</p>
  </div>
  {% endif %}
  
  <div class="grid-4">
    {% for m in results %}
    <a href="{{ url_for('user.medicine', mid=m._id, src='search') }}" class="card flex-col hover:shadow-md transition-all h-full justify-between" style="padding: 0; overflow: hidden; border: 1px solid var(--border);">
      <div style="aspect-ratio: 4/3; background: #f8fafc; display: flex; align-items: center; justify-content: center; padding: 1rem; border-bottom: 1px solid var(--border);">
        <img src="{{ url_for('static', filename=m.image) if m.image else url_for('static', filename='images/tablets.jpg') }}" onerror="this.src='{{ url_for('static', filename='images/tablets.jpg') }}'" alt="{{ m.brand }}" style="width: 100%; height: 100%; object-fit: contain;">
      </div>
      <div class="p-4">
        <h3 class="font-bold text-lg mb-1 line-clamp-1" style="color: var(--deep)">{{ m.brand }} {{ m.strength }}</h3>
        <p class="text-sm text-muted mb-2 line-clamp-2" style="height: 2.5rem; overflow: hidden;">{{ m.salt }}</p>
        <div class="flex items-center justify-between mt-3">
          <span class="font-bold text-primary">₹{{ m.mrp }}</span>
          <span class="btn btn-outline btn-sm" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">View Details</span>
        </div>
      </div>
    </a>
    {% endfor %}
  </div>
{% else %}
  <div class="card text-center py-12">
    <div class="mb-4 flex justify-center">
      <div style="background: #fef2f2; padding: 1rem; border-radius: 50%; display: inline-block;">
        <i data-lucide="search-x" style="width: 32px; height: 32px; color: var(--danger)"></i>
      </div>
    </div>
    <h3 class="font-bold text-lg mb-2">No medicines found</h3>
    <p class="text-muted">We couldn't find any medicines matching "{{ q }}".<br>Try checking the spelling or use a different search term.</p>
  </div>
{% endif %}

<style>
  .grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5rem;
  }
  @media (max-width: 1024px) {
    .grid-4 { grid-template-columns: repeat(3, 1fr); }
  }
  @media (max-width: 768px) {
    .grid-4 { grid-template-columns: repeat(2, 1fr); }
  }
  @media (max-width: 480px) {
    .grid-4 { grid-template-columns: 1fr; }
  }
  .line-clamp-1 { display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
  .line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
{% endblock %}
"""

with open(search_html_path, "w", encoding="utf-8") as f:
    f.write(search_html_content)

print("Rewrote user.py search endpoint and search.html successfully.")
