"""
Japanese Language Tutor with multimodal capabilities
Based on the translation example for pipecat 0.0.60
"""

import asyncio
import base64
import os
import sys
from io import BytesIO
from typing import List, Optional, Dict, Any, Union

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from PIL import Image

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    Frame,
    LLMMessagesFrame,
    TextFrame,
    TranscriptionFrame,
    TranscriptionMessage,
    TranscriptionUpdateFrame,
    ImageRawFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.services.elevenlabs import ElevenLabsHttpTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="INFO")

required_env_vars = [
    "GEMINI_API",  # Primary API for language model
    "OPENAI_API_KEY",  # Fallback API
    "ELEVENLABS_API_KEY",
    "DAILY_ROOM_URL",
    "DAILY_API_KEY",
    "DEEPGRAM_API_KEY"
]

for var in required_env_vars:
    if not os.getenv(var):
        logger.warning(f"Environment variable {var} is not set. Please set it in your .env file.")

DEFAULT_VOICE_IDS = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",  # Female
    "Josh": "TxGEqnHWrfWFTfGW9XjX",    # Male
}

class ImageProcessor(FrameProcessor):
    """A processor that handles image processing for the Japanese tutor."""
    
    def __init__(self):
        """Initialize the ImageProcessor."""
        super().__init__()
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process an image frame.
        
        Args:
            frame (Frame): The frame to process.
            direction (FrameDirection): The direction of the frame.
        """
        await super().process_frame(frame, direction)
        
        if isinstance(frame, ImageRawFrame):
            logger.info("Processing image frame")
            image_data = frame.image_data
            if isinstance(image_data, bytes):
                image_bytes = image_data
            else:
                buffer = BytesIO()
                image_data.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
            
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                },
                {
                    "type": "text",
                    "text": "What does this image show? Please describe it in Japanese and English."
                }
            ]
            
            context = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": content}
            ]
            
            await self.push_frame(LLMMessagesFrame(context))
        else:
            await self.push_frame(frame)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for image processing."""
        return """You are a Japanese language tutor helping beginners learn Japanese.
When shown an image, describe what you see in both Japanese and English.
For Japanese text, provide:
1. The original Japanese text
2. Romaji (Roman letters) pronunciation
3. English translation
For objects and scenes, describe them in simple Japanese with English translations.
Keep your responses concise and educational.
Focus on vocabulary that would be useful for beginners."""


class JapaneseTutorProcessor(FrameProcessor):
    """A processor that handles Japanese language tutoring responses."""

    def __init__(self):
        """Initialize the JapaneseTutorProcessor."""
        super().__init__()
        self._system_prompt = """You are a Japanese language tutor helping beginners learn Japanese.
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

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process a frame and create tutoring response.

        Args:
            frame (Frame): The frame to process.
            direction (FrameDirection): The direction of the frame.
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            logger.info(f"Processing user question: {frame.text}")
            
            text_lower = frame.text.lower()
            if "[IMAGE]" in frame.text.upper() or "camera" in text_lower or "look at" in text_lower:
                logger.info("Detected camera/image reference in text")
                if "camera" in text_lower or "look at" in text_lower:
                    response = "Please use the 'Upload Image' button to share an image."
                    await self.push_frame(TextFrame(response))
                    return
                else:
                    context = [
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": frame.text},
                    ]
                    await self.push_frame(LLMMessagesFrame(context))
            else:
                context = [
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": frame.text},
                ]
                await self.push_frame(LLMMessagesFrame(context))
        elif isinstance(frame, TextFrame):
            logger.info(f"Processing direct text input: {frame.text}")
            
            text_lower = frame.text.lower()
            if "camera" in text_lower or "look at" in text_lower:
                logger.info("Detected camera/image reference in direct text")
                response = "Please use the 'Upload Image' button to share an image."
                await self.push_frame(TextFrame(response))
                return
            
            context = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": frame.text},
            ]
            await self.push_frame(LLMMessagesFrame(context))
        else:
            await self.push_frame(frame)


class MultimodalJapaneseTutor:
    """Main class for the Multimodal Japanese Tutor application."""
    
    def __init__(self):
        """Initialize the MultimodalJapaneseTutor."""
        self.session = None
        self.transport = None
        self.task = None
        self.runner = None
        self.transcript_handler = TranscriptHandler()
    
    async def setup(self):
        """Set up the tutor pipeline and services."""
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
            daily_room_url = os.getenv("DAILY_ROOM_URL")
            daily_api_key = os.getenv("DAILY_API_KEY")
            deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
            
            default_voice_id = DEFAULT_VOICE_IDS["Rachel"]
            
            logger.info(f"Using Daily room URL: {daily_room_url}")
            logger.info(f"Using default ElevenLabs voice: Rachel (ID: {default_voice_id})")
            
            self.session = aiohttp.ClientSession()
            
            self.transport = DailyTransport(
                daily_room_url,
                "",  # Empty token (using API key mode)
                "Japanese Tutor",
                DailyParams(
                    api_key=daily_api_key,
                    audio_out_enabled=True,
                    audio_in_enabled=True,
                    vad_enabled=True,
                    vad_analyzer=SileroVADAnalyzer(),
                    vad_audio_passthrough=True,
                    video_in_enabled=True,  # Enable video input for images
                ),
            )
            
            stt = DeepgramSTTService(api_key=deepgram_api_key)
            
            tts = ElevenLabsHttpTTSService(
                api_key=elevenlabs_api_key,
                voice_id=default_voice_id,
                aiohttp_session=self.session
            )
            
            gemini_api_key = os.getenv("GEMINI_API")
            if not gemini_api_key:
                logger.warning("GEMINI_API environment variable is not set. Using OpenAI as fallback.")
                llm = OpenAILLMService(
                    api_key=openai_api_key, 
                    model="gpt-4o"
                )
            else:
                logger.info("Using Gemini API for language model")
                llm = OpenAILLMService(
                    api_key=openai_api_key, 
                    model="gpt-4o"
                )
            
            context = OpenAILLMContext()
            context_aggregator = llm.create_context_aggregator(context)
            
            jp_tutor = JapaneseTutorProcessor()
            image_processor = ImageProcessor()
            
            transcript = TranscriptProcessor()
            
            @transcript.event_handler("on_transcript_update")
            async def on_transcript_update(processor, frame):
                await self.transcript_handler.on_transcript_update(processor, frame)
            
            pipeline = Pipeline(
                [
                    self.transport.input(),
                    stt,
                    transcript.user(),  # User transcripts
                    image_processor,    # Image processor
                    jp_tutor,           # Japanese tutor processor
                    llm,                # Language model
                    tts,                # Text-to-speech
                    self.transport.output(),
                    transcript.assistant(),
                    context_aggregator.assistant(),
                ]
            )
            
            self.task = PipelineTask(
                pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    enable_metrics=True,
                    enable_usage_metrics=True,
                ),
            )
            
            @self.transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                logger.info(f"Participant joined: {participant.get('id', '')}")
                welcome_context = [
                    {"role": "system", "content": "You are a Japanese language tutor. Provide EXACTLY ONE very brief welcome in Japanese with romaji. Maximum 10 words total."},
                    {"role": "user", "content": "Start the session with a brief welcome."}
                ]
                await self.task.queue_frame(LLMMessagesFrame(welcome_context))
            
            @self.transport.event_handler("on_participant_left")
            async def on_participant_left(transport, participant, reason):
                logger.info(f"Participant left: {participant.get('id', '')}")
                await self.task.cancel()
            
            @self.transport.event_handler("on_app_message")
            async def on_app_message(transport, message, participant_id):
                logger.info(f"Received app message: {message}")
                if message.get("type") == "image_upload":
                    image_data = message.get("image_data")
                    if image_data:
                        await self.task.queue_frame(ImageRawFrame(image_data))
            
            self.runner = PipelineRunner()
            logger.info("Japanese tutor setup complete")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in tutor setup: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def run(self):
        """Run the tutor pipeline."""
        try:
            logger.info("Starting Japanese tutor session...")
            await self.runner.run(self.task)
        except Exception as e:
            logger.error(f"Error in tutor session: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if self.session:
                await self.session.close()


class TranscriptHandler:
    """Handler for transcript processing."""

    def __init__(self):
        """Initialize the TranscriptHandler with an empty list of messages."""
        self.messages: List[TranscriptionMessage] = []

    async def on_transcript_update(
        self, processor: TranscriptProcessor, frame: TranscriptionUpdateFrame
    ):
        """Handle new transcript messages.

        Args:
            processor: The TranscriptProcessor that emitted the update
            frame: TranscriptionUpdateFrame containing new messages
        """
        self.messages.extend(frame.messages)

        logger.info("New transcript messages:")
        for msg in frame.messages:
            timestamp = f"[{msg.timestamp}] " if msg.timestamp else ""
            logger.info(f"{timestamp}{msg.role}: {msg.content}")


async def main():
    """Main function to set up and run the Japanese tutor pipeline."""
    try:
        tutor = MultimodalJapaneseTutor()
        setup_success = await tutor.setup()
        
        if setup_success:
            await tutor.run()
        else:
            logger.error("Failed to set up the Japanese tutor")
            
    except KeyboardInterrupt:
        logger.info("Shutting down Japanese tutor...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down Japanese tutor...")
    except Exception as e:
        print(f"Error: {e}")
