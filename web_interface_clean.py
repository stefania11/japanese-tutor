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

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")

SYSTEM_PROMPT = """You are a Japanese language tutor helping beginners learn Japanese. 
Be concise, patient, and helpful. Your responses should be brief and to the point.
Use simple Japanese phrases and provide explanations in English. 
Focus on practical, everyday Japanese.
Always provide romaji (Roman letters) along with Japanese characters.

You can also analyze images to help with learning:
- If the user shares an image with Japanese text, you'll read and translate it
- If the user shares an image of an object or scene, you'll teach relevant vocabulary

IMPORTANT: Keep your responses short and focused. Do not repeat yourself.
If the user types "stop" or "quit", respond with only "Sayonara! Goodbye!"."""

class JapaneseTutorWeb:
    """Web interface for the Japanese Language Tutor."""
    
    def __init__(self):
        """Initialize the web interface."""
        self.app = web.Application()
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
            
            if image_data:
                content = [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": message if message else "What does this image show? Please describe it in Japanese and English."
                    }
                ]
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ]
            else:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self.conversation_history
                ]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                
                payload = {
                    "model": "gpt-4o",
                    "messages": messages
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error: {error_text}")
                        return web.json_response(
                            {"error": f"OpenAI API error: {response.status}"}, 
                            status=500
                        )
                    
                    result = await response.json()
                    assistant_message = result["choices"][0]["message"]["content"]
                    
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
