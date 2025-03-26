from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json

app = FastAPI(title="Japanese Tutor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TutorConfig(BaseModel):
    user_name: Optional[str] = None
    proficiency_level: Optional[str] = None
    interests: Optional[List[str]] = None

class TutorStatus(BaseModel):
    status: str
    message: str

@app.get("/")
async def root():
    return {"message": "Japanese Tutor API is running", "status": "online"}

@app.get("/config")
async def get_config():
    """Get the current configuration of the Japanese Tutor"""
    config = {
        "openai_api_key": os.environ.get("OPENAI_API_KEY", "").startswith("sk-"),
        "elevenlabs_api_key": os.environ.get("ELEVENLABS_API_KEY", "").startswith("sk-"),
        "elevenlabs_voice_id": os.environ.get("ELEVENLABS_VOICE_ID", ""),
        "daily_room_url": os.environ.get("DAILY_ROOM_URL", ""),
        "fal_key": os.environ.get("FAL_KEY", "") != "",
    }
    return config

@app.get("/daily-room")
async def get_daily_room():
    """Get the Daily room URL for the Japanese Tutor"""
    daily_room_url = os.environ.get("DAILY_ROOM_URL")
    if not daily_room_url:
        raise HTTPException(status_code=500, detail="Daily room URL not configured")
    return {"daily_room_url": daily_room_url}

@app.get("/instructions")
async def get_instructions():
    """Get instructions for using the Japanese Tutor"""
    return {
        "instructions": [
            "1. Visit the Daily room URL to access the Japanese Tutor",
            "2. Allow microphone and camera access when prompted",
            "3. Start speaking with the tutor in English or Japanese",
            "4. Ask for vocabulary, grammar explanations, or conversation practice",
            "5. Request images for vocabulary words",
            "6. Ask to review past mistakes or previous lessons"
        ],
        "daily_room_url": os.environ.get("DAILY_ROOM_URL", "")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
