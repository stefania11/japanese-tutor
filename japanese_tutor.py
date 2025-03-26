#
# Japanese Language Tutor using Pipecat
# A multimodal language tutor that combines voice, video, images, and text
# with memory to remember user preferences and mistakes
#

import asyncio
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import TextFrame, ImageRawFrame as ImageFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.elevenlabs import ElevenLabsHttpTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.services.fal import FalImageGenService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Constants
MEMORY_DIR = Path("/home/ubuntu/japanese_tutor/memory")
MEMORY_DIR.mkdir(exist_ok=True)
USER_PROFILE_PATH = MEMORY_DIR / "user_profile.json"
LESSON_HISTORY_PATH = MEMORY_DIR / "lesson_history.json"
MISTAKES_PATH = MEMORY_DIR / "mistakes.json"

# Initialize memory structures if they don't exist
def initialize_memory():
    if not USER_PROFILE_PATH.exists():
        with open(USER_PROFILE_PATH, "w") as f:
            json.dump({
                "name": "",
                "level": "beginner",
                "interests": [],
                "preferred_topics": [],
                "learning_goals": []
            }, f, indent=2)
    
    if not LESSON_HISTORY_PATH.exists():
        with open(LESSON_HISTORY_PATH, "w") as f:
            json.dump([], f, indent=2)
    
    if not MISTAKES_PATH.exists():
        with open(MISTAKES_PATH, "w") as f:
            json.dump({
                "vocabulary": [],
                "grammar": [],
                "pronunciation": []
            }, f, indent=2)

# Memory management functions
async def save_user_profile(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        with open(USER_PROFILE_PATH, "r") as f:
            profile = json.load(f)
        
        # Update profile with new information
        for key, value in args.items():
            if key in profile:
                profile[key] = value
        
        with open(USER_PROFILE_PATH, "w") as f:
            json.dump(profile, f, indent=2)
        
        await result_callback({"success": True, "message": "User profile updated successfully"})
    except Exception as e:
        await result_callback({"success": False, "error": str(e)})

async def get_user_profile(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        with open(USER_PROFILE_PATH, "r") as f:
            profile = json.load(f)
        
        await result_callback(profile)
    except Exception as e:
        await result_callback({"success": False, "error": str(e)})

async def record_mistake(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        mistake_type = args.get("type", "vocabulary")
        mistake = args.get("mistake", "")
        correction = args.get("correction", "")
        explanation = args.get("explanation", "")
        
        with open(MISTAKES_PATH, "r") as f:
            mistakes = json.load(f)
        
        if mistake_type in mistakes:
            mistakes[mistake_type].append({
                "mistake": mistake,
                "correction": correction,
                "explanation": explanation,
                "timestamp": datetime.now().isoformat(),
                "review_count": 0,
                "last_reviewed": None
            })
        
        with open(MISTAKES_PATH, "w") as f:
            json.dump(mistakes, f, indent=2)
        
        await result_callback({"success": True, "message": f"{mistake_type} mistake recorded"})
    except Exception as e:
        await result_callback({"success": False, "error": str(e)})

async def get_mistakes_for_review(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        mistake_type = args.get("type", None)
        limit = args.get("limit", 5)
        
        with open(MISTAKES_PATH, "r") as f:
            mistakes = json.load(f)
        
        review_items = []
        if mistake_type and mistake_type in mistakes:
            # Get mistakes of specific type
            review_items = mistakes[mistake_type][:limit]
        else:
            # Get mixed mistakes
            for type_key, type_mistakes in mistakes.items():
                review_items.extend(type_mistakes[:limit // 3 + 1])
            review_items = review_items[:limit]
        
        await result_callback({"items": review_items})
    except Exception as e:
        await result_callback({"success": False, "error": str(e)})

async def save_lesson_history(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        lesson_topic = args.get("topic", "General Japanese")
        lesson_content = args.get("content", "")
        
        with open(LESSON_HISTORY_PATH, "r") as f:
            history = json.load(f)
        
        history.append({
            "topic": lesson_topic,
            "content": lesson_content,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(LESSON_HISTORY_PATH, "w") as f:
            json.dump(history, f, indent=2)
        
        await result_callback({"success": True, "message": "Lesson history saved"})
    except Exception as e:
        await result_callback({"success": False, "error": str(e)})

async def get_lesson_history(function_name, tool_call_id, args, llm, context, result_callback):
    try:
        limit = args.get("limit", 5)
        
        with open(LESSON_HISTORY_PATH, "r") as f:
            history = json.load(f)
        
        recent_lessons = history[-limit:] if history else []
        
        await result_callback({"lessons": recent_lessons})
    except Exception as e:
        await result_callback({"success": False, "error": str(e)})

async def generate_image_for_vocabulary(function_name, tool_call_id, args, llm, context, result_callback):
    global image_gen
    
    word = args.get("word", "")
    meaning = args.get("meaning", "")
    
    prompt = f"A clear, educational illustration for the Japanese word '{word}' which means '{meaning}'. The image should be simple, colorful, and suitable for language learning."
    
    # The actual image generation will be handled by the pipeline
    # This function just signals that an image should be generated
    await result_callback({"prompt": prompt, "word": word, "meaning": meaning})

# Main application
async def main():
    # Initialize memory structures
    initialize_memory()
    
    logger.info("Japanese Tutor starting...")
    logger.info(f"Using Daily room URL: {os.getenv('DAILY_ROOM_URL')}")
    logger.info(f"Using ElevenLabs voice ID: {os.getenv('ELEVENLABS_VOICE_ID')}")
    
    async with aiohttp.ClientSession() as session:
        # For local testing without Daily, you can use:
        # from pipecat.transports.local import LocalTransport
        # transport = LocalTransport()
        
        # For production with Daily WebRTC:
        # Get Daily room URL and API key from environment
        room_url = os.getenv("DAILY_ROOM_URL", "")
        api_key = os.getenv("DAILY_TOKEN", "")
        
        if not room_url:
            logger.error("DAILY_ROOM_URL environment variable not set")
            return
            
        # Create a Daily REST helper to generate a proper token
        daily_rest_helper = DailyRESTHelper(
            daily_api_key=api_key,
            daily_api_url="https://api.daily.co/v1",
            aiohttp_session=session,
        )
        
        # Generate a token with 1 hour expiry
        try:
            token = await daily_rest_helper.get_token(room_url, 60 * 60)
            logger.info(f"Successfully generated Daily token for room {room_url}")
        except Exception as e:
            logger.error(f"Failed to generate Daily token: {e}")
            return
            
        logger.info(f"Transport initializing with room URL: {room_url}")
        
        transport = DailyTransport(
            room_url,
            token,
            "🇯🇵 Japanese Tutor",
            DailyParams(
                owner_id="japanese-tutor-bot",
                audio_out_enabled=True,
                camera_out_enabled=True,
                camera_out_width=1024,
                camera_out_height=1024,
                mic_enabled=True,  # Enable microphone input
                mic_out_enabled=True,  # Enable microphone output
                transcription_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(
                    stop_secs=0.5,  # Shorter pause detection for better responsiveness
                    threshold=0.5,  # Lower threshold to pick up speech more easily
                )),
                transcription_extra={"interim_results": True},
            ),
        )
        
        # After transport initialization, add a heartbeat mechanism
        async def heartbeat():
            """Send periodic heartbeat to keep the pipeline active and prevent idle timeout"""
            try:
                while True:
                    await asyncio.sleep(60)  # Send heartbeat every 60 seconds
                    logger.debug("Sending heartbeat to keep pipeline active")
                    # Send a no-op message to keep the pipeline active
                    # This can be anything that doesn't trigger visible behavior
                    logger.debug("Heartbeat: keeping pipeline active")
                    # Queue an empty task to keep the pipeline active
                    await task.queue_frames([])
            except asyncio.CancelledError:
                logger.debug("Heartbeat task cancelled")
            except Exception as e:
                logger.error(f"Error in heartbeat task: {str(e)}")
        
        # Start the heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat())
        
        # Text-to-Speech service
        tts = ElevenLabsHttpTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
            aiohttp_session=session,
        )
        
        # LLM service
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o", organization=None)
        
        # Image generation service
        image_gen = FalImageGenService(
            params=FalImageGenService.InputParams(image_size="square_hd"),
            aiohttp_session=session,
            key=os.getenv("FAL_KEY"),
        )
        
        # Register memory management functions
        llm.register_function("save_user_profile", save_user_profile)
        llm.register_function("get_user_profile", get_user_profile)
        llm.register_function("record_mistake", record_mistake)
        llm.register_function("get_mistakes_for_review", get_mistakes_for_review)
        llm.register_function("save_lesson_history", save_lesson_history)
        llm.register_function("get_lesson_history", get_lesson_history)
        llm.register_function("generate_image_for_vocabulary", generate_image_for_vocabulary)
        
        # Define tools for the LLM
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "save_user_profile",
                    "description": "Save or update user profile information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "User's name"
                            },
                            "level": {
                                "type": "string",
                                "enum": ["beginner", "intermediate", "advanced"],
                                "description": "User's Japanese proficiency level"
                            },
                            "interests": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "User's interests for contextual learning"
                            },
                            "preferred_topics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Topics the user prefers to learn about"
                            },
                            "learning_goals": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "User's learning goals"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_profile",
                    "description": "Get the user's profile information",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "record_mistake",
                    "description": "Record a mistake made by the user for future review",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["vocabulary", "grammar", "pronunciation"],
                                "description": "Type of mistake"
                            },
                            "mistake": {
                                "type": "string",
                                "description": "The incorrect Japanese used by the user"
                            },
                            "correction": {
                                "type": "string",
                                "description": "The correct Japanese"
                            },
                            "explanation": {
                                "type": "string",
                                "description": "Explanation of why the correction is needed"
                            }
                        },
                        "required": ["type", "mistake", "correction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_mistakes_for_review",
                    "description": "Get mistakes for review session",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["vocabulary", "grammar", "pronunciation"],
                                "description": "Type of mistakes to review (optional)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of mistakes to return"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_lesson_history",
                    "description": "Save the current lesson to history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Topic of the lesson"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content covered in the lesson"
                            }
                        },
                        "required": ["topic", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_lesson_history",
                    "description": "Get recent lesson history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of lessons to return"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_image_for_vocabulary",
                    "description": "Generate an image to illustrate a Japanese vocabulary word",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "The Japanese word to illustrate"
                            },
                            "meaning": {
                                "type": "string",
                                "description": "The English meaning of the word"
                            }
                        },
                        "required": ["word", "meaning"]
                    }
                }
            }
        ]
        
        # Define system message
        messages = [
            {
                "role": "system",
                "content": """You are a helpful and encouraging Japanese language tutor. Your goal is to help the user learn Japanese in an engaging and personalized way.

Key responsibilities:
1. Assess the user's current level and interests
2. Provide lessons tailored to their level (beginner, intermediate, advanced)
3. Teach vocabulary with visual aids (generate images for new words)
4. Correct mistakes gently and record them for future review
5. Remember the user's learning history and preferences
6. Adapt to the user's learning style and pace
7. Provide cultural context when relevant

For beginners:
- Focus on basic greetings, simple phrases, and hiragana/katakana
- Use romaji alongside Japanese characters
- Explain grammar points simply

For intermediate learners:
- Introduce more kanji and complex grammar
- Conduct parts of the conversation in Japanese
- Provide more challenging vocabulary and expressions

For advanced learners:
- Conduct most of the conversation in Japanese
- Focus on nuance, idioms, and natural expressions
- Discuss complex topics and cultural aspects

Always be encouraging, patient, and adapt to the user's needs. Use the memory functions to personalize the learning experience.
"""
            }
        ]
        
        # Create context and aggregator
        context = OpenAILLMContext(messages, tools)
        context_aggregator = llm.create_context_aggregator(context)
        
        # Define the pipeline
        pipeline = Pipeline(
            [
                transport.input(),  # Transport user input
                context_aggregator.user(),  # User responses
                llm,  # LLM
                tts,  # TTS
                image_gen,  # Image generation
                transport.output(),  # Transport bot output
                context_aggregator.assistant(),  # Assistant spoken responses
            ]
        )
        logger.info("Pipeline configured with audio input and output processing")
        
        # Create the pipeline task with a longer idle timeout (5 minutes)
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                idle_timeout_secs=300,  # 5 minutes idle timeout
            ),
        )
        
        logger.info("Pipeline configured and ready to process audio input and generate responses")
        

        
        # Event handler for when a participant joins
        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            logger.info(f"First participant joined: {participant['id']}")
            # Capture transcription for the joined participant
            await transport.capture_participant_transcription(participant["id"])
            
            # Get user profile to personalize greeting
            with open(USER_PROFILE_PATH, "r") as f:
                profile = json.load(f)
            
            # Personalized greeting based on profile
            if profile["name"]:
                greeting = f"Welcome back, {profile['name']}! Let's continue with your Japanese learning journey."
                if profile["level"] != "beginner":
                    greeting += f" 今日も一緒に日本語を勉強しましょう！ (Let's study Japanese together today too!)"
            else:
                greeting = "Welcome to your Japanese language tutor! I'm here to help you learn Japanese. Let's start by getting to know each other."
            
            # Add greeting to context
            messages.append({"role": "assistant", "content": greeting})
            
            # Start the conversation with a greeting
            await task.queue_frames([TextFrame(greeting)])
            
        # Removed unsupported event handlers for transcription events
        # Daily transport handles these events internally
        
        # Event handler for transcription messages
        @transport.event_handler("on_transcription_message")
        async def on_transcription_message(transport, message):
            try:
                # Log the raw message for debugging
                logger.debug(f"Raw transcription message: {message}")
                
                # Extract text and participant info
                text = message.get("text", "")
                participant_id = message.get("participantId", "")
                
                # Check if this is a final transcription
                is_final = False
                if "rawResponse" in message:
                    is_final = message["rawResponse"].get("is_final", False)
                else:
                    is_final = message.get("is_final", False)
                
                if text.strip():
                    logger.info(f"Received transcription from {participant_id}: {text} (final: {is_final})")
                    
                    # Only add final transcriptions to context
                    if is_final:
                        logger.info(f"Processing final transcription: {text}")
                        # Add user message to context
                        messages.append({"role": "user", "content": text})
                        # Queue the user message for processing
                        await task.queue_frames([context_aggregator.user().get_context_frame()])
                        logger.info(f"Queued user message for processing: {text}")
            except Exception as e:
                logger.error(f"Error processing transcription: {str(e)}")
                # Continue operation despite errors
        
        # Event handler for when a new participant joins
        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            try:
                participant_id = participant.get("id", "")
                participant_name = participant.get("user_name", "")
                logger.info(f"Participant joined: {participant_id}")
                
                # Modified: Only skip if this is the tutor itself AND has the correct owner_id
                # This ensures we don't skip responding to other participants
                if participant.get("owner_id") == "japanese-tutor-bot" and participant.get("is_owner", False):
                    logger.info("Skipping self (tutor) in participant handling")
                    return
                    
                if participant_id:
                    logger.info(f"Capturing transcription for participant: {participant_id}")
                    try:
                        await transport.capture_participant_transcription(participant_id)
                    except Exception as e:
                        logger.error(f"Error capturing transcription for participant {participant_id}: {str(e)}")
                    
                    # Get personalized greeting
                    greeting = "Hello! I'm your Japanese tutor. How can I help you learn Japanese today?"
                    if participant_name:
                        greeting = f"Hello {participant_name}! I'm your Japanese tutor. How can I help you learn Japanese today?"
                        
                    # Send a welcome message to new participants
                    await task.queue_frames([TextFrame(greeting)])
            except Exception as e:
                logger.error(f"Error in participant joined handler: {str(e)}")
        # Add transcription capture to first participant joined handler instead
        # since on_transcription_started is not a registered event

        # Note: on_transcription_started event is not supported by Daily transport
        # Instead, we'll capture transcription for all participants when they join

        # Add function to capture transcription for all participants
        async def capture_all_participants_transcription():
            try:
                participants = transport.participants()
                for participant_id, participant in participants.items():
                    # Skip the tutor itself
                    if participant.get("owner_id") != "japanese-tutor-bot":
                        logger.info(f"Capturing transcription for existing participant: {participant_id}")
                        try:
                            await transport.capture_participant_transcription(participant_id)
                        except Exception as e:
                            logger.error(f"Error capturing transcription for participant {participant_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error capturing all participants transcription: {str(e)}")
        
        # Event handler for when a participant leaves
        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            # Only end the session if all participants have left (except the tutor)
            participants = transport.participants()
            if len(participants) <= 1:  # Only the tutor remains
                # Save the conversation before ending
                with open(USER_PROFILE_PATH, "r") as f:
                    profile = json.load(f)
                
                if profile["name"]:
                    farewell = f"Goodbye, {profile['name']}! I've saved our progress. See you next time!"
                    if profile["level"] != "beginner":
                        farewell += " また会いましょう！ (See you again!)"
                else:
                    farewell = "Goodbye! I've saved our progress. See you next time!"
                
                await task.queue_frames([TextFrame(farewell)])
                await task.cancel()
        
        # Create and run the pipeline
        try:
            runner = PipelineRunner()
            await runner.run(task)
        finally:
            # Clean up resources
            if 'heartbeat_task' in locals():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

if __name__ == "__main__":
    asyncio.run(main())
