import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"))

class GeminiService:
    @staticmethod
    def build_product_url(slug):
        """URL শুধুমাত্র ব্যাকএন্ড থেকে জেনারেট হবে (Gemini থেকে নয়)"""
        if not slug:
            raise ValueError("Missing slug")
        return f"https://assetprim.com/product-details.php?slug={slug}"

    @staticmethod
    def generate_content(course, platform, template, custom_prompt):
        product_url = GeminiService.build_product_url(course.get('slug'))
        
        # 🛡️ Protected System Rules
        system_rules = f"""
        You are a Direct Response Copywriter for AssetPrim.
        Platform: {platform}
        
        PRODUCT DATA:
        Title: {course['title']}
        Description: {course['description']}
        
        CRITICAL PROTECTED RULES (DO NOT VIOLATE):
        1. NO URLs inside 'main_post'.
        2. Never invent features, discounts, or modules. Use ONLY the provided Product Data.
        3. The 'pinned_comment' MUST contain exactly this URL and nothing else: {product_url}
        4. End the main_post with a CTA to check the pinned comment.
        
        USER CUSTOM INSTRUCTION: {custom_prompt if custom_prompt else "Make it clean and highly engaging."}
        TEMPLATE STYLE: {template if template != "None" else "Follow user instruction primarily."}
        
        OUTPUT FORMAT: JSON ONLY (No markdown formatting)
        {{
            "headline": "String",
            "main_post": "String",
            "hashtags": ["#tag1", "#tag2"],
            "pinned_comment": "String"
        }}
        """
        
        try:
            response = model.generate_content(system_rules)
            text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(text)
            
            # 🛡️ AI Validation Check
            if "http" in result.get("main_post", ""):
                logger.warning("Validation Failed: URL found in main_post. Removing it.")
                result["main_post"] = result["main_post"].replace(product_url, "")
                
            return result, product_url
            
        except Exception as e:
            logger.error(f"Gemini Generation Error: {e}")
            return None, None
