import os
import threading
import logging
import traceback
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv

# .env লোড করা হচ্ছে
load_dotenv()

# Core মডিউলগুলো ইম্পোর্ট করা হচ্ছে
from core.automation import AutomationEngine
from core.db_manager import DatabaseManager

# ডাটাবেস ম্যানেজার ইনিশিয়ালাইজ করা হলো
db_manager = DatabaseManager()

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

# ================= 🛠️ LOGGING SETUP =================
class DashboardLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        app_state["logs"].append(log_entry)
        if len(app_state["logs"]) > 100:  
            app_state["logs"].pop(0)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
dash_handler = DashboardLogHandler()
dash_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(dash_handler)

# ================= 🌐 FLASK APP SETUP =================
app = Flask(__name__)

# Error Handler (404/Favicon এরর ইগনোর করার জন্য)
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"success": False, "error": e.description}), e.code
        
    logger.error(f"Server Error: {traceback.format_exc()}")
    return jsonify({"success": False, "error": str(e)}), 500

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify(app_state)

# 🚀 নতুন রাউট: ড্যাশবোর্ডে পোস্টগুলো দেখানোর জন্য
@app.route('/api/posts')
def get_posts():
    try:
        posts = db_manager.get_all_posts()
        return jsonify({"success": True, "posts": posts})
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return jsonify({"success": False, "posts": []})

@app.route('/api/start', methods=['POST'])
def start_automation():
    if not app_state["is_running"]:
        app_state["is_running"] = True
        app_state["processed"] = 0
        app_state["skipped"] = 0
        app_state["failed"] = 0
        app_state["logs"] = [] 
        
        logger.info("🚀 Starting Main Automation Engine...")
        
        engine = AutomationEngine(app_state)
        threading.Thread(target=engine.run, daemon=True).start()
        
        return jsonify({"success": True, "msg": "Automation Started"})
    return jsonify({"success": False, "msg": "Already Running"})

@app.route('/api/stop', methods=['POST'])
def stop_automation():
    if app_state["is_running"]:
        app_state["is_running"] = False
        logger.warning("🛑 Stop command received. Halting after current task...")
        return jsonify({"success": True, "msg": "Stopping loop..."})
    return jsonify({"success": False, "msg": "Not running"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
