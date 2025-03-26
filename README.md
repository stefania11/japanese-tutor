# Japanese Language Tutor

A multimodal Japanese language tutor built with Pipecat that combines voice, video, images, and text with memory capabilities to remember user preferences and mistakes.

## Features

- **Voice Interaction**: Natural conversation with the tutor using speech recognition and text-to-speech
- **Visual Learning**: Generates images to illustrate vocabulary and concepts
- **Personalized Learning**: Adapts to user's proficiency level and interests
- **Memory System**: Remembers user preferences, past lessons, and common mistakes
- **Spaced Repetition**: Reviews past mistakes to reinforce learning
- **Multilevel Support**: Tailored content for beginner, intermediate, and advanced learners

## Troubleshooting

### Tutor doesn't speak or respond
1. Make sure your microphone is enabled and working in the Daily room
2. Ensure the tutor is unmuted in the Daily interface
3. Try refreshing the page and rejoining the room
4. Check the tutor logs with `./status_tutor.sh` for any error messages
5. If necessary, restart the tutor with `./restart_tutor.sh`

### Daily Room Connection Issues
1. Verify your DAILY_TOKEN is correctly set in the .env file
2. The token must be a valid Daily API key with access to the room
3. Check network connectivity to Daily.co services
4. Make sure no other instance of the tutor is running in the same room
5. Restart the tutor using `./restart_tutor.sh` if it's not responding

## Requirements

- Python 3.8+
- Pipecat framework
- API keys for:
  - OpenAI (for GPT-4o)
  - ElevenLabs (for text-to-speech)
  - Daily (for WebRTC communication)
  - Fal (for image generation)

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install pipecat-ai[daily,openai,elevenlabs,fal,silero]
   ```
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   ELEVENLABS_API_KEY=your_elevenlabs_key
   ELEVENLABS_VOICE_ID=your_preferred_voice_id
   DAILY_ROOM_URL=your_daily_room_url
   DAILY_TOKEN=your_daily_token
   FAL_KEY=your_fal_key
   ```
4. Run the tutor:
   ```
   python japanese_tutor.py
   ```

## How It Works

The Japanese Language Tutor uses Pipecat's pipeline architecture to process multimodal inputs and outputs:

1. **User Input**: Captures speech through WebRTC and transcribes it
2. **Language Processing**: Uses GPT-4o to understand user input and generate appropriate responses
3. **Memory Management**: Stores and retrieves user profile, lesson history, and mistakes
4. **Multimodal Output**: Generates speech and images to enhance the learning experience

The tutor maintains three types of memory:
- **User Profile**: Stores name, proficiency level, interests, and learning goals
- **Lesson History**: Records past lessons and topics covered
- **Mistake Tracking**: Logs vocabulary, grammar, and pronunciation errors for review

## Usage

1. Join the Daily room using the provided URL
2. Speak with the tutor in English or Japanese (depending on your level)
3. Ask questions, request lessons, or practice conversation
4. The tutor will adapt to your level and provide personalized instruction

## Example Interactions

- "Can you teach me basic greetings in Japanese?"
- "How do I say 'I would like to order food' in Japanese?"
- "Can you explain the difference between は and が?"
- "Let's review my past mistakes"
- "Show me an image for the word 'sakura'"

## Troubleshooting

### Tutor doesn't speak or respond
1. Make sure your microphone is enabled and working in the Daily room
2. Ensure the tutor is unmuted in the Daily interface
3. Try refreshing the page and rejoining the room
4. Check the tutor logs with `./status_tutor.sh` for any error messages
5. If necessary, restart the tutor with `./restart_tutor.sh`

### Daily Room Connection Issues
1. Verify your DAILY_TOKEN is correctly set in the .env file
2. The token must be a valid Daily API key with access to the room
3. Check network connectivity to Daily.co services
