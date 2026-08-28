import os
import requests
import logging

logger = logging.getLogger(__name__)

# আপনার Apps Script-এর URL টি এখানে দিন অথবা Render-এর Environment Variable-এ সেট করুন
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbyTvxs7JTNc8HJ7NSMPtTk49XO3DQ4tCVbuB9BOLzG8qy4oBkQ4UFXy7rBv16ciDaabGw/exec") 
ASSETPRIM_API_TOKEN = os.getenv("ASSETPRIM_API_TOKEN")

class AssetPrimAPI:
    @staticmethod
    def fetch_active_products():
        """Apps Script এর মাধ্যমে InfinityFree থেকে ডেটা নিয়ে আসবে"""
        all_courses = []
        offset = 0
        limit = 100
        
        while True:
            try:
                # Apps Script-এ প্যারামিটার পাঠানো হচ্ছে
                url = f"{APPS_SCRIPT_URL}?token={ASSETPRIM_API_TOKEN}&limit={limit}&offset={offset}"
                logger.info(f"Fetching products via Apps Script... (Offset: {offset})")
                
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"Apps Script HTTP Error {response.status_code}. Raw response: {response.text[:200]}")
                    break
                    
                try:
                    data = response.json()
                except Exception as json_err:
                    logger.error(f"JSON Parse Error. Raw response: {response.text[:250]}")
                    break
                
                if not data.get("success"):
                    logger.error(f"API Logic Error: {data.get('error')}")
                    break
                    
                courses = data.get("products", [])
                if not courses:
                    break
                    
                all_courses.extend(courses)
                
                if not data.get("pagination", {}).get("has_more"):
                    break
                    
                offset += limit
            except Exception as e:
                logger.error(f"Failed to fetch courses: {e}")
                break
                
        return all_courses
