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
                response = requests.get(url, timeout=30)
                data = response.json()
                
                if not data.get("success"):
                    logger.error(f"API Error: {data.get('error')}")
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
