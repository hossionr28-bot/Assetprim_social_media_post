import os
import json
import time
import random
import requests
import threading
import logging
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
import google.generativeai as genai
from dotenv import load_dotenv

# --- Advanced Debugging & Logging Setup ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# .env লোড
load_dotenv()

# ================= ⚙️ CONFIGURATION =================
ASSETPRIM_API_URL = os.getenv("ASSETPRIM_API_URL", "https://assetprim.com/api/products.php")
ASSETPRIM_API_TOKEN = os.getenv("ASSETPRIM_API_TOKEN", "your_super_secret_token_here_2026")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Gemini Setup
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3.1-flash-lite')
    logger.info("✅ Gemini API Configured.")
except Exception as e:
    logger.error(f"❌ Gemini Setup Failed: {e}")

# MongoDB Setup
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info() # Force connection check
    db = mongo_client["assetprim_automation"]
    posts_col = db["generated_posts"]
    logs_col = db["automation_logs"]
    logger.info("✅ MongoDB Connected Successfully!")
except Exception as e:
    logger.error(f"❌ MongoDB Connection Error:\n{traceback.format_exc()}")
    db, posts_col, logs_col = None, None, None

# ================= 🌐 GLOBAL STATE =================
app_state = {
    "is_running": False,
    "status_msg": "Idle",
    "total_courses": 0,
    "processed": 0,
    "skipped": 0,
    "failed": 0,
    "logs": []
}

def add_log(msg, level="info"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    
    if level == "error":
        logger.error(msg)
    else:
        logger.info(msg)
        
    app_state["logs"].append(log_msg)
    if len(app_state["logs"]) > 100:
        app_state["logs"].pop(0)
    
    if logs_col is not None:
        try:
            logs_col.insert_one({"timestamp": datetime.now(), "level": level, "message": msg})
        except Exception as e:
            logger.error(f"Could not save log to DB: {e}")

# (এখানে automation_worker, fetch_all_active_courses ফাংশনগুলো আপাতত আগের মতোই থাকবে। 
# পরের ধাপে আমরা এগুলোকে core/ ফোল্ডারে সরিয়ে নেব।)
def dummy_automation_worker():
    add_log("🚀 Automation test started...", "info")
    app_state["status_msg"] = "Running test mode..."
    time.sleep(5)
    add_log("✅ Automation test completed.", "info")
    app_state["is_running"] = False
    app_state["status_msg"] = "Idle"

# ================= 🌐 FLASK WEB ROUTES =================
app = Flask(__name__)

# Error Handler for debugging
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Server Error: {traceback.format_exc()}")
    return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify(app_state)

@app.route('/api/start', methods=['POST'])
def start_automation():
    if not app_state["is_running"]:
        app_state["is_running"] = True
        threading.Thread(target=dummy_automation_worker, daemon=True).start()
        return jsonify({"success": True, "msg": "Automation Started"})
    return jsonify({"success": False, "msg": "Already Running"})

@app.route('/api/stop', methods=['POST'])
def stop_automation():
    app_state["is_running"] = False
    add_log("🛑 Stop command received.", "error")
    return jsonify({"success": True, "msg": "Stopping loop..."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
