import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"))

class GeminiService:
    @staticmethod
    def build_product_url(slug):
        if not slug:
            raise ValueError("Missing slug")
        return f"https://assetprim.com/product-details.php?slug={slug}"

    @staticmethod
    def generate_content(course, platform, template, custom_prompt):
        product_url = GeminiService.build_product_url(course.get('slug'))
        
        # 1. Base System Rules (Strictly Enforced)
        base_rules = f"""
        Role: Direct Response Copywriter for AssetPrim.
        Platform: {platform}
        Product Title: {course.get('title')}
        Product Description: {course.get('description')}
        
        CRITICAL RULES (DO NOT VIOLATE):
        - NO URLs inside 'main_post'.
        - 'pinned_comment' MUST contain exactly this URL: {product_url}
        - Do not invent fake features, modules, or discounts.
        - Output strictly in JSON format.
        """
        
        # 2. Template Logic
        template_instruction = ""
        if template != "None":
            template_instruction = f"TEMPLATE STYLE: Apply a '{template}' marketing framework."
            
        # 3. Final Prompt Assembly
        final_prompt = f"""
        {base_rules}
        
        USER INSTRUCTION: {custom_prompt if custom_prompt else "Create clean, highly engaging content based on the product description."}
        {template_instruction}
        
        JSON FORMAT REQUIRED:
        {{
            "headline": "...",
            "main_post": "...",
            "hashtags": ["#tag1"],
            "pinned_comment": "..."
        }}
        """
        
        try:
            response = model.generate_content(final_prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(text)
            
            # AI Validation: Force remove URL if AI hallucinates it into main_post
            if "http" in result.get("main_post", ""):
                result["main_post"] = result["main_post"].replace(product_url, "").strip()
                
            return result, product_url
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return None, None
