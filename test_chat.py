import json
from bson import ObjectId
from pymongo import MongoClient
import re
from dotenv import load_dotenv
import os

load_dotenv()

db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))[os.getenv("DB_NAME", "medilens")]

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

try:
    print("Testing search_medicines...")
    res = _search_medicines(db, {"query": "calpol"})
    print("Result:", res)
except Exception as e:
    import traceback
    print("Error:", traceback.format_exc())

import groq
key = os.getenv("GROQ_API_KEY")
print("Key length:", len(key) if key else 0)
client = groq.Groq(api_key=key)

try:
    print("Testing Groq tool call...")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_medicines",
                "description": "Search the MediLens database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    }
                }
            }
        }
    ]
    r = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=1000,
        messages=[{"role": "user", "content": "is calpol here"}],
        tools=tools,
        tool_choice="auto"
    )
    msg = r.choices[0].message
    print("Groq response msg:", msg)
    if msg.tool_calls:
        print("Tool call details:", msg.tool_calls[0])
        args = json.loads(msg.tool_calls[0].function.arguments)
        print("Parsed args:", args)
        
        # Test serialization of formatted_messages
        tool_call = msg.tool_calls[0]
        formatted_messages = [{"role": "user", "content": "is calpol here"}]
        formatted_messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [{
                "id": tool_call.id,
                "type": "function",
                "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments}
            }]
        })
        search_result = _search_medicines(db, args)
        formatted_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": search_result
        })
        print("Formatted messages for 2nd hop:", formatted_messages)
        
        r2 = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=1000,
            messages=formatted_messages
        )
        print("Final reply:", r2.choices[0].message.content)
except Exception as e:
    import traceback
    print("Error:", traceback.format_exc())
