import os

admin_health_tips_html = """{% extends "base.html" %}
{% block title %}Manage Health Tips · Admin{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-2xl font-bold m-0">Health Tips Management</h1>
    <p class="text-sm text-muted">Manage health tips displayed on customer dashboards.</p>
  </div>
  <a href="{{ url_for('admin.health_tip_new') }}" class="btn btn-primary"><i data-lucide="plus"></i> Add Health Tip</a>
</div>

<div class="card mb-6">
  <form method="get" action="{{ url_for('admin.health_tips') }}" class="flex gap-4 items-end" style="flex-wrap: wrap;">
    <div style="flex:1; min-width: 200px;">
      <label class="font-semibold text-sm">Search English Title</label>
      <input name="q" value="{{ filters.q or '' }}" placeholder="Search health tips..." class="w-full">
    </div>
    <div>
      <label class="font-semibold text-sm">Category</label>
      <select name="category">
        <option value="">All Categories</option>
        <option value="Nutrition" {% if filters.category == 'Nutrition' %}selected{% endif %}>Nutrition</option>
        <option value="Hydration" {% if filters.category == 'Hydration' %}selected{% endif %}>Hydration</option>
        <option value="Sleep" {% if filters.category == 'Sleep' %}selected{% endif %}>Sleep</option>
        <option value="Hygiene" {% if filters.category == 'Hygiene' %}selected{% endif %}>Hygiene</option>
        <option value="Medicine Safety" {% if filters.category == 'Medicine Safety' %}selected{% endif %}>Medicine Safety</option>
        <option value="Physical Activity" {% if filters.category == 'Physical Activity' %}selected{% endif %}>Physical Activity</option>
        <option value="General Health" {% if filters.category == 'General Health' %}selected{% endif %}>General Health</option>
      </select>
    </div>
    <div>
      <label class="font-semibold text-sm">Status</label>
      <select name="status">
        <option value="">All Statuses</option>
        <option value="active" {% if filters.status == 'active' %}selected{% endif %}>Active</option>
        <option value="inactive" {% if filters.status == 'inactive' %}selected{% endif %}>Inactive</option>
      </select>
    </div>
    <div>
      <label class="font-semibold text-sm">Sort By</label>
      <select name="sort">
        <option value="newest" {% if filters.sort == 'newest' %}selected{% endif %}>Newest</option>
        <option value="oldest" {% if filters.sort == 'oldest' %}selected{% endif %}>Oldest</option>
        <option value="a-z" {% if filters.sort == 'a-z' %}selected{% endif %}>Title A-Z</option>
        <option value="z-a" {% if filters.sort == 'z-a' %}selected{% endif %}>Title Z-A</option>
      </select>
    </div>
    <button type="submit" class="btn">Filter</button>
    <a href="{{ url_for('admin.health_tips') }}" class="btn btn-outline">Clear</a>
  </form>
</div>

<div class="card p-0" style="overflow-x:auto;">
  <table class="w-full text-left" style="border-collapse: collapse;">
    <thead>
      <tr style="border-bottom: 1px solid var(--border); background: var(--bg);">
        <th class="p-3 font-semibold">Image</th>
        <th class="p-3 font-semibold">Title (English)</th>
        <th class="p-3 font-semibold">Category</th>
        <th class="p-3 font-semibold">Status</th>
        <th class="p-3 font-semibold">Created Date</th>
        <th class="p-3 font-semibold text-right">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for tip in tips %}
      <tr style="border-bottom: 1px solid var(--border);">
        <td class="p-3">
            {% if tip.media and tip.media.file_id %}
            <img src="{{ url_for('health_tip_media', file_id=tip.media.file_id) }}" alt="Tip" style="width:50px; height:50px; object-fit:cover; border-radius:4px;">
            {% else %}
            <div style="width:50px; height:50px; background:#eee; border-radius:4px; display:flex; align-items:center; justify-content:center;">
                <i data-lucide="image" style="color:#aaa;"></i>
            </div>
            {% endif %}
        </td>
        <td class="p-3 font-semibold">{{ tip.content.en.title }}</td>
        <td class="p-3"><span class="badge">{{ tip.category }}</span></td>
        <td class="p-3">
            <span class="badge {% if tip.status == 'active' %}badge-success{% endif %}">{{ tip.status|title }}</span>
        </td>
        <td class="p-3 text-sm text-muted">{{ tip.created_at.strftime('%Y-%m-%d') }}</td>
        <td class="p-3 text-right">
          <div class="flex items-center justify-end gap-2">
            <a href="{{ url_for('admin.health_tip_edit', tid=tip._id) }}" class="btn btn-outline btn-sm">Edit</a>
            <form method="post" action="{{ url_for('admin.health_tip_delete', tid=tip._id) }}" onsubmit="return confirm('Are you sure you want to delete this tip?');">
              <input type="hidden" name="csrf" value="{{ csrf }}">
              <button type="submit" class="btn btn-sm" style="background:#fee2e2; color:#ef4444; border:1px solid #fca5a5;">Delete</button>
            </form>
          </div>
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="6" class="p-8 text-center text-muted">No health tips found.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
"""

admin_health_tip_form_html = """{% extends "base.html" %}
{% block title %}{{ 'Edit' if edit else 'Add' }} Health Tip · Admin{% endblock %}
{% block content %}
<div class="mb-6">
  <a href="{{ url_for('admin.health_tips') }}" class="text-sm font-semibold" style="color:var(--primary)"><i data-lucide="arrow-left" style="width:16px; display:inline"></i> Back to Health Tips</a>
  <h1 class="text-2xl font-bold m-0 mt-2">{{ 'Edit' if edit else 'Add' }} Health Tip</h1>
</div>

<div class="card max-w-2xl">
  <form method="post" enctype="multipart/form-data" class="flex-col gap-4">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    
    <div>
      <label class="font-semibold block mb-1">Category</label>
      <input name="category" value="{{ tip.category or '' }}" required class="w-full" placeholder="e.g. Nutrition, Hydration, Sleep">
    </div>

    <div>
      <label class="font-semibold block mb-1">Status</label>
      <select name="status" class="w-full">
        <option value="active" {% if tip.status == 'active' %}selected{% endif %}>Active</option>
        <option value="inactive" {% if tip.status == 'inactive' %}selected{% endif %}>Inactive</option>
      </select>
    </div>

    <div style="border-top: 1px solid var(--border); padding-top: 1rem; margin-top: 0.5rem;">
      <h3 class="font-bold text-lg mb-2">English Content</h3>
      <div class="flex-col gap-2">
        <input name="en_title" value="{{ tip.content.en.title if tip.content else '' }}" required class="w-full" placeholder="English Title">
        <textarea name="en_text" required class="w-full" placeholder="English Description" rows="3">{{ tip.content.en.description if tip.content else '' }}</textarea>
      </div>
    </div>

    <div style="border-top: 1px solid var(--border); padding-top: 1rem; margin-top: 0.5rem;">
      <h3 class="font-bold text-lg mb-2">Tamil Content (Optional)</h3>
      <div class="flex-col gap-2">
        <input name="ta_title" value="{{ tip.content.ta.title if tip.content else '' }}" class="w-full" placeholder="Tamil Title">
        <textarea name="ta_text" class="w-full" placeholder="Tamil Description" rows="3">{{ tip.content.ta.description if tip.content else '' }}</textarea>
      </div>
    </div>

    <div style="border-top: 1px solid var(--border); padding-top: 1rem; margin-top: 0.5rem;">
      <h3 class="font-bold text-lg mb-2">Hindi Content (Optional)</h3>
      <div class="flex-col gap-2">
        <input name="hi_title" value="{{ tip.content.hi.title if tip.content else '' }}" class="w-full" placeholder="Hindi Title">
        <textarea name="hi_text" class="w-full" placeholder="Hindi Description" rows="3">{{ tip.content.hi.description if tip.content else '' }}</textarea>
      </div>
    </div>

    <div style="border-top: 1px solid var(--border); padding-top: 1rem; margin-top: 0.5rem;">
      <h3 class="font-bold text-lg mb-2">Media</h3>
      {% if tip.media and tip.media.file_id %}
      <div class="mb-4">
        <p class="text-sm font-semibold mb-2">Current Image:</p>
        <img src="{{ url_for('health_tip_media', file_id=tip.media.file_id) }}" style="max-width:200px; border-radius:4px; border:1px solid var(--border);">
      </div>
      {% endif %}
      <label class="font-semibold block mb-1">Upload New Image {% if not edit %}(Required){% endif %}</label>
      <input type="file" name="image" accept="image/*" class="w-full" {% if not edit %}required{% endif %}>
    </div>

    <button type="submit" class="btn btn-primary w-full mt-4">{{ 'Save Changes' if edit else 'Create Health Tip' }}</button>
  </form>
</div>
{% endblock %}
"""

tpl_dir = r"d:\flask_Mongo\medilens_final\medilens\templates"
with open(os.path.join(tpl_dir, "admin_health_tips.html"), "w", encoding="utf-8") as f:
    f.write(admin_health_tips_html)

with open(os.path.join(tpl_dir, "admin_health_tip_form.html"), "w", encoding="utf-8") as f:
    f.write(admin_health_tip_form_html)

print("Templates created.")
