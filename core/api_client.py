import os
import requests
import logging

logger = logging.getLogger(__name__)

ASSETPRIM_API_URL = os.getenv("ASSETPRIM_API_URL", "https://assetprim.com/api/products.php")
ASSETPRIM_API_TOKEN = os.getenv("ASSETPRIM_API_TOKEN")

class AssetPrimAPI:
    @staticmethod
    def fetch_active_products():
        """সব অ্যাক্টিভ কোর্স নিয়ে আসবে (Pagination সহ)"""
        all_courses = []
        offset = 0
        limit = 100
        
        while True:
            try:
                url = f"{ASSETPRIM_API_URL}?token={ASSETPRIM_API_TOKEN}&limit={limit}&offset={offset}"
                logger.info(f"Fetching products from API... (Offset: {offset})")
                
                response = requests.get(url, timeout=30)
                
                # যদি সার্ভার 200 OK না দেয়
                if response.status_code != 200:
                    logger.error(f"API HTTP Error {response.status_code}. Raw response: {response.text[:200]}")
                    break
                    
                # JSON পার্স করার চেষ্টা
                try:
                    data = response.json()
                except Exception as json_err:
                    logger.error(f"JSON Parse Error: API did not return JSON. Raw response: {response.text[:250]}")
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
