import os
import json
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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
        
        # 🛡️ Protected System Rules (More Strict)
        base_rules = f"""
        Role: Direct Response Copywriter for AssetPrim.
        Platform: {platform}
        
        PRODUCT DATA:
        Title: {course.get('title', 'Unknown')}
        Description: {course.get('description', 'No description provided')}
        
        CRITICAL PROTECTED RULES (DO NOT VIOLATE):
        1. You MUST generate a complete and engaging 'main_post'. DO NOT leave it blank.
        2. NO URLs inside 'main_post'.
        3. Never invent features, discounts, or modules. Use ONLY the provided Product Data.
        4. The 'pinned_comment' MUST contain exactly this URL and nothing else: {product_url}
        5. Generate 3 to 5 relevant hashtags.
        """
        
        template_instruction = ""
        if template and template != "None":
            template_instruction = f"TEMPLATE STYLE: Apply a '{template}' marketing framework."
            
        final_prompt = f"""
        {base_rules}
        
        USER INSTRUCTION: {custom_prompt if custom_prompt else "Write a highly converting, clean promotional post."}
        {template_instruction}
        
        OUTPUT FORMAT: Provide ONLY a valid JSON object. Do not include markdown formatting like ```json.
        {{
            "headline": "Catchy headline here",
            "main_post": "Write the full post body here. Must be detailed.",
            "hashtags": ["#tag1", "#tag2", "#tag3"],
            "pinned_comment": "Check out the course here: {product_url}"
        }}
        """
        
        try:
            # 🛡️ Safety filters bypass for marketing/affiliate keywords
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            response = model.generate_content(
                final_prompt,
                safety_settings=safety_settings
            )
            
            # JSON Clean up and parsing
            text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(text)
            
            # 🛡️ Smart Key Extraction (To prevent missing data if Gemini renames keys)
            clean_result = {
                "headline": result.get("headline", result.get("Headline", "")),
                "main_post": result.get("main_post", result.get("Main_Post", result.get("MainPost", ""))),
                "hashtags": result.get("hashtags", result.get("Hashtags", [])),
                "pinned_comment": result.get("pinned_comment", product_url)
            }
            
            # 🛡️ Fallback if AI somehow still leaves main_post empty
            if not clean_result["main_post"] or len(clean_result["main_post"]) < 10:
                clean_result["main_post"] = f"Explore the incredible benefits of {course.get('title')}. Check the pinned comment for details!"

            # 🛡️ AI Validation Check: Force remove URL from main_post
            if "http" in clean_result["main_post"]:
                logger.warning("Validation Failed: URL found in main_post. Removing it.")
                clean_result["main_post"] = clean_result["main_post"].replace(product_url, "")
                
            return clean_result, product_url
            
        except Exception as e:
            logger.error(f"Gemini Generation Error: {e}")
            return None, None
