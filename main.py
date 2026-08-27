import os
import json
import time
import random
import requests
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from pymongo import MongoClient
import google.generativeai as genai
from dotenv import load_dotenv

# .env ফাইল লোড করা (লোকাল টেস্টের জন্য)
load_dotenv()

# ================= ⚙️ CONFIGURATION =================
ASSETPRIM_API_URL = os.getenv("ASSETPRIM_API_URL", "https://assetprim.com/api/products.php")
ASSETPRIM_API_TOKEN = os.getenv("ASSETPRIM_API_TOKEN", "your_super_secret_token_here_2026")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')

# MongoDB Setup
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["assetprim_automation"]
    posts_col = db["generated_posts"]
    logs_col = db["automation_logs"]
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")
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

def add_log(msg):
    log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(log_msg)
    app_state["logs"].append(log_msg)
    if len(app_state["logs"]) > 50:
        app_state["logs"].pop(0)
    
    # ডাটাবেসে লগ সেভ করা
    if logs_col is not None:
        logs_col.insert_one({"timestamp": datetime.now(), "message": msg})


# ================= 🛠️ CORE FUNCTIONS =================
def fetch_all_active_courses():
    """API থেকে লুপ চালিয়ে সবগুলো কোর্স নিয়ে আসবে"""
    all_courses = []
    offset = 0
    limit = 100
    
    while True:
        try:
            url = f"{ASSETPRIM_API_URL}?token={ASSETPRIM_API_TOKEN}&limit={limit}&offset={offset}"
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if not data.get("success"):
                add_log(f"❌ API Error: {data.get('error')}")
                break
                
            courses = data.get("products", [])
            all_courses.extend(courses)
            
            if not data.get("pagination", {}).get("has_more"):
                break
                
            offset += limit
        except Exception as e:
            add_log(f"❌ Failed to fetch courses: {e}")
            break
            
    return all_courses

def build_product_url(slug):
    """কোর্সের সঠিক URL জেনারেট করা"""
    return f"https://assetprim.com/product-details.php?slug={slug}"

def generate_social_post(course, platform):
    """Gemini API দিয়ে কন্টেন্ট জেনারেট করা"""
    product_url = build_product_url(course['slug'])
    
    prompt = f"""You are a Direct Response Copywriter for 'AssetPrim'.
Write a highly engaging {platform} post for the following product.

Product Title: {course['title']}
Product Description: {course['description']}

CRITICAL RULES:
1. DO NOT include any links or URLs in the 'main_post'.
2. The 'main_post' must focus on benefits and what's inside. Keep it clean and readable.
3. The 'pinned_comment' MUST contain exactly this URL: {product_url}
4. DO NOT invent fake features, modules, or discounts. Use only provided info.
5. Provide the output strictly as a JSON object without markdown formatting.

JSON Format:
{{
    "headline": "Catchy headline",
    "main_post": "The main social media copy (no links). End with a CTA to check the pinned comment.",
    "hashtags": ["#tag1", "#tag2"],
    "pinned_comment": "Check out the full details and enroll here: {product_url}"
}}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        add_log(f"❌ Gemini Error for ID {course['id']}: {e}")
        return None


# ================= 🚀 AUTOMATION ENGINE =================
def automation_worker():
    """ব্যাকগ্রাউন্ডে পোস্ট জেনারেট করার ইঞ্জিন"""
    add_log("🚀 Automation Started...")
    app_state["status_msg"] = "Fetching courses from AssetPrim API..."
    
    # 1. সব কোর্স ফেচ করা
    courses = fetch_all_active_courses()
    app_state["total_courses"] = len(courses)
    add_log(f"📦 Found {len(courses)} active courses.")
    
    platforms_to_generate = ["Facebook", "Instagram", "Telegram"]
    
    for course in courses:
        if not app_state["is_running"]:
            add_log("🛑 Automation Stopped by User.")
            break
            
        course_id = course["id"]
        title_short = course["title"][:30] + "..."
        
        for platform in platforms_to_generate:
            if not app_state["is_running"]:
                break
                
            # 2. Duplicate Check (MongoDB)
            if posts_col is not None:
                exists = posts_col.find_one({"course_id": course_id, "platform": platform})
                if exists:
                    app_state["skipped"] += 1
                    add_log(f"⏭️ Skipped (Already exists): {title_short} for {platform}")
                    continue
            
            # 3. Generate Post
            app_state["status_msg"] = f"Generating {platform} post for ID: {course_id}"
            add_log(f"⏳ Generating {platform} post for: {title_short}")
            
            generated_data = generate_social_post(course, platform)
            
            if generated_data:
                # 4. Save to Database
                save_data = {
                    "course_id": course_id,
                    "course_title": course["title"],
                    "product_url": build_product_url(course["slug"]),
                    "platform": platform,
                    "headline": generated_data.get("headline", ""),
                    "main_post": generated_data.get("main_post", ""),
                    "pinned_comment": generated_data.get("pinned_comment", ""),
                    "hashtags": generated_data.get("hashtags", []),
                    "status": "Generated",
                    "created_at": datetime.now()
                }
                if posts_col is not None:
                    posts_col.insert_one(save_data)
                
                app_state["processed"] += 1
                add_log(f"✅ Success: Saved {platform} post for ID {course_id}")
            else:
                app_state["failed"] += 1
                
            # API Rate Limit থেকে বাঁচতে একটু ব্রেক
            time.sleep(random.uniform(3.5, 6.5))

    app_state["is_running"] = False
    app_state["status_msg"] = "Automation Completed!"
    add_log("🏁 Automation Cycle Finished.")


# ================= 🌐 FLASK WEB ROUTES =================
app = Flask(__name__)

@app.route('/')
def dashboard():
    # সাময়িকভাবে একটি সিম্পল ড্যাশবোর্ড (পরবর্তীতে templates/index.html এ সরাবো)
    return """
    <html>
        <head><title>AssetPrim Automation</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🚀 AssetPrim Social Media Automation</h2>
            <p><strong>Status:</strong> <span id="status">Loading...</span></p>
            <p><strong>Courses Found:</strong> <span id="total">0</span> | <strong>Generated:</strong> <span id="processed">0</span> | <strong>Skipped:</strong> <span id="skipped">0</span></p>
            <button onclick="fetch('/start', {method: 'POST'})" style="padding: 10px; background: green; color: white;">Start Automation</button>
            <button onclick="fetch('/stop', {method: 'POST'})" style="padding: 10px; background: red; color: white;">Stop Automation</button>
            <hr>
            <h3>Live Logs:</h3>
            <pre id="logs" style="background: #222; color: #0f0; padding: 10px; height: 300px; overflow-y: scroll;"></pre>
            
            <script>
                setInterval(() => {
                    fetch('/status').then(r => r.json()).then(data => {
                        document.getElementById('status').innerText = data.status_msg + (data.is_running ? ' (Running)' : ' (Stopped)');
                        document.getElementById('total').innerText = data.total_courses;
                        document.getElementById('processed').innerText = data.processed;
                        document.getElementById('skipped').innerText = data.skipped;
                        document.getElementById('logs').innerText = data.logs.join('\\n');
                    });
                }, 2000);
            </script>
        </body>
    </html>
    """

@app.route('/status')
def status():
    return jsonify(app_state)

@app.route('/start', methods=['POST'])
def start_automation():
    if not app_state["is_running"]:
        app_state["is_running"] = True
        app_state["processed"] = 0
        app_state["skipped"] = 0
        threading.Thread(target=automation_worker, daemon=True).start()
        return jsonify({"msg": "Automation Started"})
    return jsonify({"msg": "Already Running"})

@app.route('/stop', methods=['POST'])
def stop_automation():
    app_state["is_running"] = False
    return jsonify({"msg": "Stopping loop..."})

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)