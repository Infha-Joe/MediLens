import re

user_py_path = r"d:\flask_Mongo\medilens_final\medilens\user.py"

with open(user_py_path, "r", encoding="utf-8") as f:
    user_code = f.read()

# Pattern to remove all order routes
user_code = re.sub(r'@bp\.route\("/order/new"\).*?def order_new\(\):.*?return render_template\("order_form\.html"[^\)]+\)', '', user_code, flags=re.DOTALL)
user_code = re.sub(r'@bp\.route\("/order", methods=\["POST"\]\).*?def order_create\(\):.*?return redirect\(url_for\("user\.orders"\)\)', '', user_code, flags=re.DOTALL)
user_code = re.sub(r'@bp\.route\("/orders"\).*?def orders\(\):.*?return render_template\("user_orders\.html", rows=rows\)', '', user_code, flags=re.DOTALL)
user_code = re.sub(r'@bp\.route\("/orders/<oid>/cancel", methods=\["POST"\]\).*?def order_cancel\(oid\):.*?return redirect\(url_for\("user\.orders"\)\)', '', user_code, flags=re.DOTALL)
user_code = re.sub(r'@bp\.route\("/prescription/<name>"\).*?def prescription\(name\):.*?return send_from_directory\(current_app\.config\["UPLOAD_FOLDER"\], name\)', '', user_code, flags=re.DOTALL)

with open(user_py_path, "w", encoding="utf-8") as f:
    f.write(user_code)

print("Removed order routes from user.py")
