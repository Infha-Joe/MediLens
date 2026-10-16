import json
import re
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, abort, current_app, jsonify, redirect, request, session, url_for, render_template

from auth import role_required, login_required
from db import get_db

bp = Blueprint("chat", __name__, url_prefix="/chat")
LANGS = {"en": "English", "ta": "Tamil", "hi": "Hindi"}
HOURLY_LIMIT = 50

SYSTEM = """You are MediLens AI, an intelligent medicine information assistant.
You provide information based primarily on the MediLens master database details provided below, supplemented by general, safe medical knowledge.

SAFETY RULES:
1. NEVER diagnose diseases.
2. NEVER prescribe medicines or recommend starting/stopping medication.
3. NEVER recommend dosage changes.
4. DO NOT provide personalized medical treatment.
5. MediLens does not support medicine purchasing or ordering. If asked to buy/order medicine, explicitly state: "MediLens does not currently support medicine purchasing or ordering. You can use Find Pharmacies to check which pharmacies in your selected city have this medicine."
6. If a medicine is not provided in the context, explicitly state "I don't have that information in the MediLens database" and offer safe general knowledge if possible, but clarify it's general.
7. Keep responses clean, well-formatted using Markdown (bullet points, bold text).
7. If you perform a search, output the results as structured cards. Use the EXACT format below, including markdown links:

--------------------------------
**[Medicine Name/Brand]**
Salt: [Salt]
Price: ₹[Price]
Status: [In Stock / Out of Stock]
Pharmacy: [Pharmacy Name]

[View Medicine](/user/medicine/[medicine_id])
--------------------------------

MEDILENS CONTEXT:
{facts}"""

def _oid(v):
    if not v: return None
    try:
        return ObjectId(v)
    except (InvalidId, TypeError):
        return None

def _lang():
    return session.get("lang") if session.get("lang") in LANGS else "en"

def _search_medicines(db, filters):
    query = {}
    if filters.get("query"):
        rx = {"$regex": re.escape(filters.get("query")), "$options": "i"}
        query["$or"] = [{"brand": rx}, {"salt": rx}, {"uses": rx}]
    
    medicines_cursor = db.medicines.find(query).limit(5)
    results = []
    for med in medicines_cursor:
        med_id = med["_id"]
        inv_query = {"medicine_id": med_id}
        if filters.get("in_stock_only"):
            inv_query["qty"] = {"$gt": 0}
        
        valid_invs = []
        for inv in db.inventory.find(inv_query):
            price = inv.get("price", 0)
            if filters.get("min_price") and price < filters.get("min_price"):
                continue
            if filters.get("max_price") and price > filters.get("max_price"):
                continue
            valid_invs.append(inv)
            
        if (filters.get("min_price") or filters.get("max_price") or filters.get("in_stock_only") or filters.get("nearest_pharmacy")) and not valid_invs:
            continue
            
        pharmacies = []
        for inv in valid_invs:
            shop = db.shops.find_one({"_id": inv["shop_id"]})
            if shop:
                pharmacies.append({
                    "name": shop.get("name"),
                    "shop_id": str(shop.get("_id")),
                    "price": inv.get("price"),
                    "stock": inv.get("qty")
                })
                
        results.append({
            "medicine_id": str(med_id),
            "brand": med.get("brand"),
            "salt": med.get("salt"),
            "mrp": med.get("mrp"),
            "rx_required": med.get("rx_required"),
            "pharmacies": pharmacies
        })
        
    if not results:
        return "No medicines found matching these filters."
    return json.dumps(results)

def _model(system, messages, max_tokens=1000, db=None):
    key = current_app.config.get("GROQ_API_KEY")
    if not key:
        return None
    import groq
    try:
        formatted_messages = [{"role": "system", "content": system}] + messages
        client = groq.Groq(api_key=key)
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_medicines",
                    "description": "Search the MediLens database for medicines and pharmacies based on user filters. Use this when the user asks to find a medicine, check availability, or filter by price.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The medicine name, brand, salt, or condition. Empty if just filtering."},
                            "min_price": {"type": "number", "description": "Minimum price in rupees"},
                            "max_price": {"type": "number", "description": "Maximum price in rupees"},
                            "in_stock_only": {"type": "boolean", "description": "True if user wants only in-stock medicines"},
                            "nearest_pharmacy": {"type": "boolean", "description": "True if user asks for nearby pharmacies"}
                        }
                    }
                }
            }
        ]

        r = client.chat.completions.create(
            model=current_app.config.get("CHAT_MODEL", "openai/gpt-oss-120b"),
            max_tokens=max_tokens,
            messages=formatted_messages,
            tools=tools,
            tool_choice="auto"
        )
        
        msg = r.choices[0].message
        if msg.tool_calls and db is not None:
            tool_call = msg.tool_calls[0]
            if tool_call.function.name == "search_medicines":
                args = json.loads(tool_call.function.arguments)
                search_result = _search_medicines(db, args)
                
                formatted_messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments}
                    }]
                })
                formatted_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": search_result
                })
                
                r2 = client.chat.completions.create(
                    model=current_app.config.get("CHAT_MODEL", "openai/gpt-oss-120b"),
                    max_tokens=max_tokens,
                    messages=formatted_messages
                )
                return r2.choices[0].message.content.strip()
                
        return msg.content.strip()
    except Exception as e:
        current_app.logger.exception("Groq call failed")
        return None

def _facts(db, med):
    if not med:
        return "No specific medicine selected by the user. Answer general questions safely."
    alts = [f'{a["brand"]} (MRP Rs {a["mrp"]})' for a in db.medicines.find(
        {"salt": med["salt"], "strength": med["strength"], "_id": {"$ne": med["_id"]}}).limit(6)]
    
    return (f"Medicine: {med.get('brand')} {med.get('strength')}\n"
            f"Salt: {med.get('salt')}\n"
            f"MRP: Rs {med.get('mrp')}\n"
            f"Prescription required: {'Yes' if med.get('rx_required') else 'No'}\n"
            f"Used for: {med.get('uses')}\n"
            f"Common side effects: {med.get('side_effects')}\n"
            f"Warnings: {med.get('warnings')}\n"
            f"Alternatives: {', '.join(alts) or 'none listed'}")


@bp.route("/", methods=["GET"])
@login_required
def chat_page():
    session_id = request.args.get("session_id", "")
    medicine_id = request.args.get("medicine_id", "")
    return render_template("chat_page.html", session_id=session_id, medicine_id=medicine_id)


@bp.route("/api/history", methods=["GET"])
@login_required
def api_history():
    db = get_db()
    uid = ObjectId(session["user_id"])
    sessions = list(db.chat_sessions.find({"user_id": uid}).sort("updated_at", -1).limit(20))
    for s in sessions:
        s["_id"] = str(s["_id"])
        s.pop("messages", None)
    return jsonify(sessions=sessions)


@bp.route("/api/session/<session_id>", methods=["GET"])
@login_required
def api_session(session_id):
    db = get_db()
    uid = ObjectId(session["user_id"])
    sid = _oid(session_id)
    if not sid: return jsonify(error="Invalid session"), 400
    
    sess = db.chat_sessions.find_one({"_id": sid, "user_id": uid})
    if not sess: return jsonify(error="Session not found"), 404
    
    return jsonify({
        "title": sess.get("title", "MediLens AI"),
        "medicine_id": str(sess.get("medicine_id")) if sess.get("medicine_id") else None,
        "messages": [{"role": m["role"], "content": m["content"]} for m in sess.get("messages", [])]
    })


@bp.route("/api/context/<medicine_id>", methods=["GET"])
@login_required
def api_context(medicine_id):
    db = get_db()
    mid = _oid(medicine_id)
    med = db.medicines.find_one({"_id": mid}) if mid else None
    if not med: return jsonify(error="Not found")
    
    return jsonify({
        "brand": med.get("brand"),
        "strength": med.get("strength"),
        "salt": med.get("salt"),
        "mrp": med.get("mrp"),
        "uses": med.get("uses"),
        "rx_required": med.get("rx_required")
    })


@bp.route("/api/ask", methods=["POST"])
@login_required
def api_ask():
    if not current_app.config.get("GROQ_API_KEY"):
        return jsonify(error="MediLens AI is not configured yet. Please add GROQ_API_KEY to your .env file."), 200

    db = get_db()
    uid = ObjectId(session["user_id"])
    data = request.get_json(silent=True) or {}
    text = data.get("message", "").strip()[:1000]
    
    if not text:
        return jsonify(error="Message cannot be empty."), 400
        
    sid = _oid(data.get("session_id"))
    mid = _oid(data.get("medicine_id"))
    
    med = db.medicines.find_one({"_id": mid}) if mid else None

    # Load or create session
    is_new = False
    if sid:
        sess = db.chat_sessions.find_one({"_id": sid, "user_id": uid})
        if not sess: return jsonify(error="Session not found"), 404
    else:
        is_new = True
        # Generate title
        title = (text[:30] + "...") if len(text) > 30 else text
        sess = {
            "user_id": uid,
            "title": title,
            "medicine_id": mid,
            "messages": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        res = db.chat_sessions.insert_one(sess)
        sid = res.inserted_id
        sess["_id"] = sid

    # Prepare Messages
    turns = []
    for m in sess.get("messages", [])[-10:]:
        turns.append({"role": m["role"] if m["role"] in ["user", "assistant"] else "assistant", "content": m["content"]})
        
    turns.append({"role": "user", "content": text})
    
    # Language injection
    lang_name = LANGS.get(_lang(), "English")
    system_prompt = SYSTEM.format(facts=_facts(db, med))
    system_prompt += f"\n\nIMPORTANT: The user has selected {lang_name} as their language. ALL your responses MUST be in {lang_name}. Do NOT answer in English unless the selected language is English."
    
    # Disable ordering instruction
    system_prompt += "\n\nCRITICAL RULE: Medicine ordering is disabled. If the user asks to buy, order, or checkout, politely state that MediLens currently provides medicine information and availability only, and ordering is not available."

    # Call AI
    reply = _model(system_prompt, turns, db=db)
    if not reply:
        return jsonify(error="Sorry, MediLens AI is temporarily unavailable. Please try again."), 200

    now = datetime.now(timezone.utc)
    db.chat_sessions.update_one({"_id": sid}, {
        "$push": {"messages": {"$each": [
            {"role": "user", "content": text, "at": now},
            {"role": "assistant", "content": reply, "at": now}
        ]}},
        "$set": {"updated_at": now}
    })
    
    return jsonify(reply=reply, session_id=str(sid))

# Keep backward compatibility for the inline UI if someone accesses it directly
@bp.route("/<mid>/ask", methods=["POST"])
@role_required("user")
def ask(mid):
    return jsonify(error="Inline chat deprecated. Please use the Ask MediLens AI button."), 400

@bp.route("/<mid>/history")
@role_required("user")
def history(mid):
    return jsonify(messages=[])
    
@bp.route("/lang/<code>", methods=["POST"])
@role_required("user")
def set_lang(code):
    if code in LANGS:
        session["lang"] = code
        get_db().users.update_one({"_id": ObjectId(session["user_id"])}, {"$set": {"lang": code}})
    return redirect(request.referrer or url_for("user.home"))

@bp.route("/<mid>/translate", methods=["POST"])
@role_required("user")
def translate(mid):
    db, oid, lang = get_db(), _oid(mid), _lang()
    med = db.medicines.find_one({"_id": oid}) or abort(404)
    if lang == "en" or (med.get("i18n") or {}).get(lang):
        return jsonify(ok=True)
    prompt = (f"Translate these medicine details into {LANGS[lang]} in simple words. Keep the medical meaning exact. "
              'Return ONLY JSON with keys "uses", "side_effects", "warnings".\n' +
              json.dumps({k: med[k] for k in ("uses", "side_effects", "warnings")}))
    raw = _model("You are a careful medical translator.", [{"role": "user", "content": prompt}], 800)
    if not raw: return jsonify(error="Translation isn't available right now."), 503
    try:
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        db.medicines.update_one({"_id": oid}, {"$set": {f"i18n.{lang}": {k: data[k] for k in ("uses", "side_effects", "warnings")}}})
        return jsonify(ok=True)
    except Exception:
        return jsonify(error="Failed to translate"), 503
