import os
import uuid
import asyncio

import httpx
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Twilio credentials
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
agent_id = os.getenv("AGENT_ID")
ngrok_endpoint = os.getenv("NGROK_ENDPOINT")


# Use FastAPI lifespan to properly manage the HTTP client
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient()
    yield
    await client.aclose()  # Properly close the client on shutdown


app = FastAPI(lifespan=lifespan)


async def get_agent_stream_initialise():
    url = f"{ngrok_endpoint}/agent/stream/initialise?agent_id={agent_id}"
    headers = {'accept': 'application/json'}

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": str(e)}


@app.post("/voice")
async def voice(SpeechResult: str = Form("")):
    response = VoiceResponse()
    caller_speech = SpeechResult.strip().lower()

    if caller_speech:
        print(f"Caller said: {caller_speech}")

        if "cancel the call" in caller_speech:
            response.say("Goodbye!", voice="Polly.Joanna")
            response.hangup()
        else:
            send_message_task = asyncio.create_task(send_message(caller_speech))

            # Properly unpack the result from asyncio.gather
            send_message_response, = await asyncio.gather(send_message_task)

            gather = Gather(
                input="speech",
                action="/voice",
                timeout=3.5,
                speech_model="phone_call",
                enhanced=True,
                speech_timeout="auto",
                barge_in=False
            )
            gather.say(f"{send_message_response}", voice="Polly.Joanna")
            response.append(gather)
    else:
        response.say("Hello! This is your AI-powered receptionist, How can I help?")
        gather = Gather(
            input="speech",
            action="/voice",
            timeout=2,
            speech_model="phone_call",
            enhanced=True,
            speech_timeout="auto",
            barge_in=False
        )
        response.append(gather)

    return Response(content=str(response), media_type="text/xml")


async def send_message(message: str):
    thread_id = str(uuid.uuid4())
    url = f"{ngrok_endpoint}/agent/stream/messages?agent_id={agent_id}&thread_id={thread_id}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {"message": message}

    try:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()
        messages = response_data.get("messages", [])
        content = " ".join(msg["content"] for msg in messages if "content" in msg).strip()
        print("SendMessageResponse", content)
        return content
    except httpx.RequestError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
