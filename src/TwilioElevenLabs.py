import os
import uuid
import asyncio
import logging
import httpx
import uvicorn
import aiohttp
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import Response, StreamingResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Configure logging
logger = logging.getLogger("TwilioElevenLabsStreaming")
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv(dotenv_path="resources/.env")
logger.debug("Environment variables loaded.")

# Twilio configuration
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
agent_id = os.getenv("AGENT_ID")
ngrok_endpoint = os.getenv("SLOTWISE_NGROK_ENDPOINT")
local_ngrok_endpoint = os.getenv("LOCAL_NGROK_ENDPOINT")
logger.debug("Twilio and agent configuration loaded.")

# ElevenLabs configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    logger.error("ELEVENLABS_API_KEY is not set. Please set it in your environment or .env file.")
    raise ValueError("ELEVENLABS_API_KEY is not set.")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL_ID = "eleven_turbo_v2"

# Dictionary to store text before converting to speech
audio_text_store = {}


# Use FastAPI lifespan to properly manage the HTTP client
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient()
    logger.info("HTTP client created.")
    yield
    await client.aclose()
    logger.info("HTTP client closed.")


app = FastAPI(lifespan=lifespan)


@app.post("/voice")
async def voice(SpeechResult: str = Form("")):
    """
    This endpoint is called by Twilio when a caller speaks.
    """
    response = VoiceResponse()
    caller_speech = SpeechResult.strip().lower() if SpeechResult else ""
    logger.debug("Received speech result: '%s'", caller_speech)

    if caller_speech:
        logger.info("Caller said: %s", caller_speech)
        if "cancel the call" in caller_speech:
            logger.info("Caller requested to cancel the call.")
            audio_id = str(uuid.uuid4())
            audio_text_store[audio_id] = "Goodbye!"
            audio_url = f"{local_ngrok_endpoint}/audio/{audio_id}"
            response.play(audio_url)
            response.hangup()
        else:
            send_message_response = await send_message(caller_speech)

            # Store agent response text for streaming
            audio_id = str(uuid.uuid4())
            audio_text_store[audio_id] = send_message_response
            audio_url = f"{local_ngrok_endpoint}/audio/{audio_id}"

            gather = Gather(
                input="speech",
                action="/voice",
                timeout=3.5,
                speech_model="phone_call",
                enhanced=True,
                speech_timeout="auto",
                barge_in=False
            )
            gather.play(audio_url)
            response.append(gather)

    else:
        logger.info("No speech result provided. Sending initial greeting using ElevenLabs.")
        audio_id = str(uuid.uuid4())
        audio_text_store[audio_id] = "Hello! This is your AI-powered receptionist. How can I help?"
        audio_url = f"{local_ngrok_endpoint}/audio/{audio_id}"

        gather = Gather(
            input="speech",
            action="/voice",
            timeout=3.5,
            speech_model="phone_call",
            enhanced=True,
            speech_timeout="auto",
            barge_in=False
        )
        gather.play(audio_url)
        response.append(gather)

    return Response(content=str(response), media_type="text/xml")


async def send_message(message: str):
    """
    Send the caller's message to an agent and return a text response.
    """
    thread_id = str(uuid.uuid4())
    url = f"{ngrok_endpoint}/agent/stream/messages?agent_id={agent_id}&thread_id={thread_id}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {"message": message}
    logger.debug("Sending POST request to %s with data: %s", url, data)

    try:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()
        messages = response_data.get("messages", [])
        content = " ".join(msg["content"] for msg in messages if "content" in msg).strip()
        logger.info("Agent response content: %s", content)
        return content
    except httpx.RequestError as e:
        logger.error("Error in send_message: %s", e)
        return "I'm sorry, I couldn't process that request."


async def text_to_speech_stream(text: str):
    """
    Stream text-to-speech audio from ElevenLabs instead of waiting for full MP3.
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                logger.error(f"Failed to stream audio: {response.status}")
                raise HTTPException(status_code=500, detail="Audio streaming failed")

            async for chunk in response.content.iter_any():
                yield chunk  # yielding bytes directly


@app.get("/audio/{audio_id}")
async def get_audio_stream(audio_id: str):
    """
    Serve streamed audio directly to Twilio instead of waiting for full generation.
    """
    logger.debug("Streaming audio for text-to-speech.")

    text_to_speak = audio_text_store.get(audio_id)  # Retrieve the response text
    if not text_to_speak:
        logger.error("Text not found for ID: %s", audio_id)
        raise HTTPException(status_code=404, detail="Text not found")

    return StreamingResponse(text_to_speech_stream(text_to_speak), media_type="audio/mpeg")


async def get_agent_stream_initialise():
    url = f"{ngrok_endpoint}/agent/stream/initialise?agent_id={agent_id}"
    headers = {'accept': 'application/json'}

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    port = 5000
    logger.info("Starting application on port %s", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
