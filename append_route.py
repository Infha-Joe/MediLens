import os
path = r"d:\flask_Mongo\medilens_final\medilens\user.py"

code = """
@bp.route("/pharmacy/<shop_id>")
@role_required("user")
def pharmacy_details(shop_id):
    db = get_db()
    shop = db.shops.find_one({"_id": _oid(shop_id)})
    if not shop:
        flash("Pharmacy not found.", "error")
        return redirect(url_for("user.shops"))
    
    inventory_cursor = db.inventory.find({"shop_id": shop["_id"], "qty": {"$gt": 0}})
    inventory_items = []
    for inv in inventory_cursor:
        med = db.medicines.find_one({"_id": inv["medicine_id"]})
        if med:
            inventory_items.append({"med": med, "inv": inv})
            
    back_city = request.args.get("city", "")
    back_mid = request.args.get("mid", "")
    
    return render_template("pharmacy_details.html", shop=shop, inventory=inventory_items, back_city=back_city, back_mid=back_mid)
"""

with open(path, "a", encoding="utf-8") as f:
    f.write(code)
print("Appended route.")
