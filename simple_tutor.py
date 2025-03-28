#
# Japanese Language Tutor with multimodal capabilities
# Based on the translation example for pipecat 0.0.60
#

import asyncio
import os
import sys
from typing import List

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    Frame,
    LLMMessagesFrame,
    TextFrame,
    TranscriptionFrame,
    TranscriptionMessage,
    TranscriptionUpdateFrame,
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

# Load environment variables
load_dotenv(override=True)

# Set up logging
logger.remove(0)
logger.add(sys.stderr, level="INFO")

# Manually set environment variables if not present
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = ""
if not os.getenv("ELEVENLABS_API_KEY"):
    os.environ["ELEVENLABS_API_KEY"] = ""
if not os.getenv("DAILY_ROOM_URL"):
    os.environ["DAILY_ROOM_URL"] = "https://hackidemia.daily.co/Japanese_tutor_custom"
if not os.getenv("DAILY_API_KEY"):
    os.environ["DAILY_API_KEY"] = ""
if not os.getenv("DEEPGRAM_API_KEY"):
    os.environ["DEEPGRAM_API_KEY"] = ""

# Default ElevenLabs voice IDs
DEFAULT_VOICE_IDS = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",  # Female
    "Josh": "TxGEqnHWrfWFTfGW9XjX",    # Male
}

# Custom processor for Japanese tutoring
class JapaneseTutorProcessor(FrameProcessor):
    """A processor that handles Japanese language tutoring responses."""

    def __init__(self):
        """Initialize the JapaneseTutorProcessor."""
        super().__init__()
        self._system_prompt = """You are a Japanese language tutor helping beginners learn Japanese. 
Be concise, patient, and helpful. Your responses should be brief and to the point.
Use simple Japanese phrases and provide explanations in English. 
Focus on practical, everyday Japanese.
Always provide romaji (Roman letters) along with Japanese characters.
IMPORTANT: Keep your responses short and focused. Do not repeat yourself.
DO NOT say "it looks like your message got cut off" - just answer the question directly.
If the user types "stop" or "quit", respond with only "Sayonara! Goodbye!".."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process a frame and create tutoring response.

        Args:
            frame (Frame): The frame to process.
            direction (FrameDirection): The direction of the frame.
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            logger.info(f"Processing user question: {frame.text}")
            context = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": frame.text},
            ]
            await self.push_frame(LLMMessagesFrame(context))
        elif isinstance(frame, TextFrame):
            # Handle direct text input for testing
            logger.info(f"Processing direct text input: {frame.text}")
            context = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": frame.text},
            ]
            await self.push_frame(LLMMessagesFrame(context))
        else:
            await self.push_frame(frame)


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

        # Log the new messages
        logger.info("New transcript messages:")
        for msg in frame.messages:
            timestamp = f"[{msg.timestamp}] " if msg.timestamp else ""
            logger.info(f"{timestamp}{msg.role}: {msg.content}")


async def main():
    """Main function to set up and run the Japanese tutor pipeline."""
    try:
        # Get environment variables
        openai_api_key = os.getenv("OPENAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        daily_room_url = os.getenv("DAILY_ROOM_URL")
        daily_api_key = os.getenv("DAILY_API_KEY")
        deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        
        # Use a default voice
        default_voice_id = DEFAULT_VOICE_IDS["Rachel"]
        
        logger.info(f"Using Daily room URL: {daily_room_url}")
        logger.info(f"Using default ElevenLabs voice: Josh (ID: {default_voice_id})")
        
        async with aiohttp.ClientSession() as session:
            # Set up transport
            transport = DailyTransport(
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
                ),
            )
            
            # Set up speech-to-text service
            stt = DeepgramSTTService(api_key=deepgram_api_key)
            
            # Set up text-to-speech service
            tts = ElevenLabsHttpTTSService(
                api_key=elevenlabs_api_key,
                voice_id=default_voice_id,
                aiohttp_session=session
            )
            
            # Set up LLM service
            llm = OpenAILLMService(api_key=openai_api_key, model="gpt-4o")
            
            # Initialize context for tracking conversation
            context = OpenAILLMContext()
            context_aggregator = llm.create_context_aggregator(context)
            
            # Set up Japanese tutor processor
            jp_tutor = JapaneseTutorProcessor()
            
            # Set up transcript processor
            transcript = TranscriptProcessor()
            transcript_handler = TranscriptHandler()
            
            # Register event handler for transcript updates
            @transcript.event_handler("on_transcript_update")
            async def on_transcript_update(processor, frame):
                await transcript_handler.on_transcript_update(processor, frame)
            
            # Create the pipeline
            pipeline = Pipeline(
                [
                    transport.input(),
                    stt,
                    transcript.user(),  # User transcripts
                    jp_tutor,           # Japanese tutor processor
                    llm,                # Language model
                    tts,                # Text-to-speech
                    transport.output(),
                    transcript.assistant(),
                    context_aggregator.assistant(),
                ]
            )
            
            # Create task with appropriate parameters
            task = PipelineTask(
                pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    enable_metrics=True,
                    enable_usage_metrics=True,
                ),
            )
            
            # Event handlers for transport
            @transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                logger.info(f"Participant joined: {participant.get('id', '')}")
                # Send welcome message
                welcome_context = [
                    {"role": "system", "content": "You are a Japanese language tutor keep greeting brief."},
                ]
                await task.queue_frame(LLMMessagesFrame(welcome_context))
            
            @transport.event_handler("on_participant_left")
            async def on_participant_left(transport, participant, reason):
                logger.info(f"Participant left: {participant.get('id', '')}")
                await task.cancel()
            
            # Create and run the pipeline
            runner = PipelineRunner()
            logger.info("Starting Japanese tutor session...")
            
            await runner.run(task)
            
    except Exception as e:
        logger.error(f"Error in tutor session: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Run the application
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down Japanese tutor...")
    except Exception as e:
        print(f"Error: {e}")