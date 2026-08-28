import os
from datetime import datetime
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI")

class DatabaseManager:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client["assetprim_automation"]
            self.posts_col = self.db["generated_posts"]
            self.logs_col = self.db["automation_logs"]
            self.failed_col = self.db["failed_jobs"]
        except Exception as e:
            logger.error(f"MongoDB Config Error: {e}")
            self.db = None

    def check_duplicate(self, course_id, platform):
        """চেক করবে আগে থেকে এই প্ল্যাটফর্মের জন্য পোস্ট আছে কি না"""
        if self.db is None: return False
        return self.posts_col.find_one({"course_id": course_id, "platform": platform}) is not None

    def save_post(self, data):
        """জেনারেট করা পোস্ট সেভ করবে"""
        if self.db is not None:
            data['created_at'] = datetime.now()
            self.posts_col.insert_one(data)

    def log_error(self, course_id, platform, reason):
        """ব্যর্থ হওয়া জবগুলো সেভ করবে"""
        if self.db is not None:
            self.failed_col.insert_one({
                "course_id": course_id,
                "platform": platform,
                "reason": reason,
                "created_at": datetime.now()
            })

    def get_all_posts(self):
        """ড্যাশবোর্ডে দেখানোর জন্য ডাটাবেস থেকে সব পোস্ট নিয়ে আসবে"""
        if self.db is None: return []
        posts = []
        # লেটেস্ট পোস্টগুলো আগে দেখাবে (sort by created_at descending)
        for post in self.posts_col.find({}, {"_id": 0}).sort("created_at", -1):
            if "created_at" in post:
                # ড্যাশবোর্ডে সুন্দরভাবে দেখানোর জন্য ডেট ফরম্যাট করা হচ্ছে
                post["created_at"] = post["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            posts.append(post)
        return posts
