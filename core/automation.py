import time
import random
import logging
from core.db_manager import DatabaseManager
from core.api_client import AssetPrimAPI
from core.gemini_service import GeminiService

logger = logging.getLogger(__name__)
db = DatabaseManager()

class AutomationEngine:
    def __init__(self, app_state):
        self.app_state = app_state
        self.platforms = ["Facebook", "Instagram", "Telegram"] # Configurable later
    
    def run(self):
        self.app_state["status_msg"] = "Fetching active products..."
        courses = AssetPrimAPI.fetch_active_products()
        self.app_state["total_courses"] = len(courses)
        
        for course in courses:
            if not self.app_state["is_running"]:
                logger.info("Automation Stopped by User.")
                break
                
            course_id = course.get("id")
            
            for platform in self.platforms:
                if not self.app_state["is_running"]: break
                
                # ১. Duplicate Check
                if db.check_duplicate(course_id, platform):
                    self.app_state["skipped"] += 1
                    continue
                
                self.app_state["status_msg"] = f"Processing ID {course_id} for {platform}"
                
                # ২. Generate Content
                custom_prompt = "" # Later fetched from UI settings
                template = "None"
                
                generated_data, product_url = GeminiService.generate_content(course, platform, template, custom_prompt)
                
                # ৩. Error Handling & Save
                if generated_data:
                    save_payload = {
                        "course_id": course_id,
                        "course_title": course.get("title"),
                        "product_photo": course.get("photo"),
                        "product_url": product_url,
                        "platform": platform,
                        **generated_data
                    }
                    db.save_post(save_payload)
                    self.app_state["processed"] += 1
                else:
                    db.log_error(course_id, platform, "Gemini parsing or network error")
                    self.app_state["failed"] += 1
                
                # ৪. Rate Limiting (Batch processing delay)
                time.sleep(random.uniform(3.0, 5.0))

        self.app_state["is_running"] = False
        self.app_state["status_msg"] = "Automation Completed!"
