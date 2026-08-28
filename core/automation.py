import time
import logging
from core.db_manager import DatabaseManager
from core.api_client import AssetPrimAPI
from core.gemini_service import GeminiService

logger = logging.getLogger(__name__)
db = DatabaseManager()

class AutomationEngine:
    def __init__(self, app_state, selected_platforms=None, template="None", custom_prompt=""):
        self.app_state = app_state
        self.platforms = selected_platforms if selected_platforms else ["Facebook", "Instagram", "Telegram"]
        self.template = template
        self.custom_prompt = custom_prompt
    
    def run(self):
        self.app_state["status_msg"] = "Fetching active products..."
        courses = AssetPrimAPI.fetch_active_products()
        self.app_state["total_courses"] = len(courses)
        
        for course in courses:
            if not self.app_state["is_running"]:
                logger.info("Automation Stopped by User.")
                break
                
            course_id = course.get("id")
            if not course.get("slug"):
                db.log_error(course_id, "All", "Missing slug")
                continue
            
            for platform in self.platforms:
                if not self.app_state["is_running"]: break
                
                # Duplicate Check
                if db.check_duplicate(course_id, platform):
                    self.app_state["skipped"] += 1
                    continue
                
                self.app_state["status_msg"] = f"Processing ID {course_id} for {platform}"
                
                # Generate Content
                generated_data, product_url = GeminiService.generate_content(
                    course, platform, self.template, self.custom_prompt
                )
                
                if generated_data:
                    save_payload = {
                        "course_id": course_id,
                        "course_title": course.get("title"),
                        "product_photo": course.get("photo"),
                        "product_url": product_url,
                        "platform": platform,
                        "template_used": self.template,
                        **generated_data
                    }
                    db.save_post(save_payload)
                    self.app_state["processed"] += 1
                    logger.info(f"✅ Generated {platform} post for: {course.get('title')[:20]}...")
                else:
                    db.log_error(course_id, platform, "Content generation failed")
                    self.app_state["failed"] += 1
                
                # Rate Limiting: 14 posts per minute (~4.3 seconds delay)
                time.sleep(4.3)

        self.app_state["is_running"] = False
        self.app_state["status_msg"] = "Automation Completed!"
