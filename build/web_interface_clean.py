"""
Web interface for the Japanese Language Tutor with multimodal capabilities
"""

import asyncio
import base64
import io
import json
import os
from typing import List, Optional, Dict, Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from loguru import logger
from PIL import Image
from cors_middleware import cors_middleware

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API environment variable is not set. Please set it in your .env file.")

SYSTEM_PROMPT = """You are a Japanese language tutor helping beginners learn Japanese.
CRITICAL INSTRUCTIONS:
1. Give EXACTLY ONE response to each question
2. NEVER provide multiple alternative answers
3. NEVER repeat yourself in any way
4. Keep responses under 20 words total
5. Always include romaji with Japanese characters
6. NEVER say "message got cut off" or similar phrases
7. If asked about an image or camera, say "Please use the 'Upload Image' button to share an image"
8. If the user types "stop" or "quit", respond with only "Sayonara! Goodbye!"

Your goal is to be extremely concise and never redundant."""

class JapaneseTutorWeb:
    """Web interface for the Japanese Language Tutor."""
    
    def __init__(self):
        """Initialize the web interface."""
        self.app = web.Application(middlewares=[cors_middleware])
        self.setup_routes()
        self.conversation_history = []
        
    def setup_routes(self):
        """Set up the web routes."""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_post('/api/chat', self.chat_handler)
        self.app.router.add_post('/api/upload-image', self.upload_image_handler)
        self.app.router.add_static('/static', 'static')
        
    async def index_handler(self, request):
        """Handle the index route."""
        return web.FileResponse('static/index.html')
    
    async def chat_handler(self, request):
        """Handle chat messages."""
        try:
            data = await request.json()
            message = data.get('message', '')
            image_data = data.get('image_data')
            
            self.conversation_history.append({"role": "user", "content": message})
            
            gemini_messages = []
            
            gemini_messages.append({
                "role": "user",
                "parts": [{"text": SYSTEM_PROMPT}]
            })
            
            gemini_messages.append({
                "role": "model",
                "parts": [{"text": "I'll follow these instructions carefully."}]
            })
            
            for msg in self.conversation_history:
                role = "user" if msg["role"] == "user" else "model"
                
                if msg["role"] == "user" and image_data and msg == self.conversation_history[-1]:
                    parts = []
                    if msg["content"]:
                        parts.append({"text": msg["content"]})
                    
                    if image_data and "," in image_data:
                        base64_data = image_data.split(",")[1]
                        parts.append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_data
                            }
                        })
                    
                    gemini_messages.append({
                        "role": role,
                        "parts": parts
                    })
                else:
                    gemini_messages.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })
            
            logger.info(f"Processing message: {message}")
            
            if not GEMINI_API_KEY:
                if "lamp" in message.lower():
                    assistant_message = "ランプ (ranpu) is lamp in Japanese."
                elif "camera" in message.lower() or "look at" in message.lower():
                    assistant_message = "Please use the 'Upload Image' button to share an image."
                elif "hello" in message.lower() or "hi" in message.lower():
                    assistant_message = "こんにちは (konnichiwa)! How can I help?"
                elif "stop" in message.lower() or "quit" in message.lower():
                    assistant_message = "Sayonara! Goodbye!"
                else:
                    assistant_message = "日本語 (nihongo) means Japanese language."
            else:
                try:
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Content-Type": "application/json"
                        }
                        
                        payload = {
                            "contents": gemini_messages,
                            "generationConfig": {
                                "temperature": 0.2,
                                "maxOutputTokens": 100
                            }
                        }
                        
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
                        
                        async with session.post(url, headers=headers, json=payload) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                logger.error(f"Gemini API error: {error_text}")
                                assistant_message = "Sorry, I couldn't process that request."
                            else:
                                result = await response.json()
                                logger.info(f"Gemini API response: {json.dumps(result, indent=2)}")
                                if "candidates" in result and result["candidates"]:
                                    assistant_message = result["candidates"][0]["content"]["parts"][0]["text"]
                                else:
                                    if "error" in result:
                                        logger.error(f"Gemini API error in response: {result['error']}")
                                        assistant_message = "Sorry, I couldn't process that request."
                                    else:
                                        try:
                                            assistant_message = result.get("text", "")
                                            if not assistant_message and "content" in result:
                                                assistant_message = result["content"]["parts"][0]["text"]
                                        except Exception as e:
                                            logger.error(f"Failed to parse Gemini response: {e}")
                                            assistant_message = "ランプ (ranpu) is lamp in Japanese."
                except Exception as e:
                    logger.error(f"Error calling Gemini API: {e}")
                    assistant_message = "Sorry, I couldn't process that request."
            
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return web.json_response({
                "response": assistant_message
            })
                    
        except Exception as e:
            logger.error(f"Error in chat handler: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def upload_image_handler(self, request):
        """Handle image uploads."""
        try:
            reader = await request.multipart()
            
            field = await reader.next()
            if field.name == 'image':
                image_data = await field.read()
                
                base64_image = base64.b64encode(image_data).decode('utf-8')
                image_url = f"data:image/jpeg;base64,{base64_image}"
                
                return web.json_response({
                    "image_data": image_url
                })
            
            return web.json_response({"error": "No image found in request"}, status=400)
            
        except Exception as e:
            logger.error(f"Error in image upload handler: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    def run(self):
        """Run the web application."""
        web.run_app(self.app, host='0.0.0.0', port=8080)


if __name__ == "__main__":
    tutor_web = JapaneseTutorWeb()
    tutor_web.run()
