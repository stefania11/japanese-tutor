#!/usr/bin/env python3
"""
Japanese Language Tutor using Pipecat
"""
import os
import json
import time
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Check if required environment variables are set
required_vars = [
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "DAILY_ROOM_URL",
    "DAILY_TOKEN",
    "FAL_KEY"
]

missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these variables in your .env file or environment.")
    exit(1)

print("Starting Japanese Language Tutor...")
print(f"Daily Room URL: {os.environ.get('DAILY_ROOM_URL')}")
print(f"ElevenLabs Voice ID: {os.environ.get('ELEVENLABS_VOICE_ID')}")

# Create memory directory
memory_dir = Path("./memory")
memory_dir.mkdir(exist_ok=True)

# Initialize memory files if they don't exist
user_profile_path = memory_dir / "user_profile.json"
lesson_history_path = memory_dir / "lesson_history.json"
mistakes_path = memory_dir / "mistakes.json"

if not user_profile_path.exists():
    with open(user_profile_path, "w") as f:
        json.dump({"name": "", "proficiency_level": "beginner", "interests": []}, f)

if not lesson_history_path.exists():
    with open(lesson_history_path, "w") as f:
        json.dump([], f)

if not mistakes_path.exists():
    with open(mistakes_path, "w") as f:
        json.dump([], f)

print("Memory system initialized.")
print("Connecting to Daily room...")

# Simulate connecting to Daily room
print("Waiting for user to join the room...")
time.sleep(2)
print("User joined the room.")

# Simulate conversation
async def main():
    print("\nJapanese Tutor: こんにちは! Hello! I'm your Japanese language tutor.")
    print("Japanese Tutor: I'll help you learn Japanese based on your interests and proficiency level.")
    print("Japanese Tutor: I'll remember your progress and mistakes to provide personalized lessons.")
    print("Japanese Tutor: You can ask me to teach you vocabulary, grammar, or have a conversation practice.")
    
    # Simulate waiting for user input
    print("\nWaiting for user input...")
    await asyncio.sleep(5)
    
    print("\nUser: Can you teach me basic greetings in Japanese?")
    await asyncio.sleep(2)
    
    print("\nJapanese Tutor: Of course! Here are some basic Japanese greetings:")
    print("Japanese Tutor: 1. こんにちは (Konnichiwa) - Hello/Good afternoon")
    print("Japanese Tutor: 2. おはようございます (Ohayou gozaimasu) - Good morning")
    print("Japanese Tutor: 3. こんばんは (Konbanwa) - Good evening")
    print("Japanese Tutor: 4. さようなら (Sayounara) - Goodbye")
    print("Japanese Tutor: 5. ありがとう (Arigatou) - Thank you")
    
    # Simulate generating an image
    print("\nGenerating image for 'こんにちは'...")
    await asyncio.sleep(3)
    print("Image generated! (This would display an image in the actual application)")
    
    # Update memory
    print("\nUpdating memory with lesson on greetings...")
    with open(lesson_history_path, "r") as f:
        history = json.load(f)
    
    history.append({
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "topic": "Basic Greetings",
        "content": ["こんにちは", "おはようございます", "こんばんは", "さようなら", "ありがとう"]
    })
    
    with open(lesson_history_path, "w") as f:
        json.dump(history, f, indent=2)
    
    print("Memory updated successfully.")
    
    # Simulate waiting for more user input
    print("\nWaiting for user input...")
    await asyncio.sleep(5)
    
    print("\nUser: How do I say 'My name is John' in Japanese?")
    await asyncio.sleep(2)
    
    print("\nJapanese Tutor: To say 'My name is John' in Japanese, you would say:")
    print("Japanese Tutor: 私の名前はジョンです。(Watashi no namae wa John desu.)")
    print("Japanese Tutor: Let's break it down:")
    print("Japanese Tutor: - 私 (Watashi) - I/me")
    print("Japanese Tutor: - の (no) - possessive particle ('s)")
    print("Japanese Tutor: - 名前 (namae) - name")
    print("Japanese Tutor: - は (wa) - topic marker")
    print("Japanese Tutor: - ジョン (John) - your name")
    print("Japanese Tutor: - です (desu) - is/am/are")
    
    print("\nJapanese Tutor: Would you like to practice this phrase?")
    
    # Simulate ending the session
    print("\nSimulation complete. In the actual application, this would continue as an interactive session.")
    print("The tutor would remember your progress and mistakes for future sessions.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting Japanese Language Tutor. さようなら!")
