from app import create_app
from chat import _model
from db import get_db

app = create_app()

with app.app_context():
    db = get_db()
    system_prompt = "You are a test AI."
    turns = [{"role": "user", "content": "is calpol here"}]
    
    # We will temporarily mock the logger to print the exception to stdout
    import logging
    import traceback
    
    try:
        reply = _model(system_prompt, turns, db=db)
        print("Reply:", reply)
    except Exception as e:
        print("EXCEPTION CAUGHT BY SCRIPT:", traceback.format_exc())
