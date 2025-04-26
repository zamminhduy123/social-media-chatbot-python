from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
from google import genai
from google.genai.chats import Chat

import random
from datetime import datetime
import time

from SessionController import SessionController
from gemini_prompt import DEFAULT_RESPONSE

# === Load environment variables ===
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")

# === CONFIG ===
FACEBOOK_VERSION = 'v22.0'

# === Configure Gemini ===
# Configure Gemini
client = genai.Client(api_key=API_KEY)

app = Flask(__name__)

chat_sessions = SessionController(client)


# === === === === === === === ACTUAL WORK FUNCTION
def get_gemini_response(user_message, sender_id) -> str:
    # actually generate response:
    try:
        chat_session = chat_sessions.get_session(sender_id)
        chat: Chat = chat_session["chat"] # type: ignore
        response = chat.send_message(user_message)
        return response.text # type: ignore
    except Exception as e:
        print("Gemini error:", e)
        return DEFAULT_RESPONSE


def send_typing_indicator(psid):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "sender_action": "typing_on"
    }
    headers = {'Content-Type': 'application/json'}
    requests.post(url, headers=headers, json=payload)

def send_facebook_message(psid, message):
    url = f"https://graph.facebook.com/{FACEBOOK_VERSION}/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": message}
    }
    headers = {'Content-Type': 'application/json'}
    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print("Error sending message to FB:", e)

# === === === === === === === ROUTING FUNCTION
def handle_user_message(message_event):
    # get time 
    current_time = int(datetime.now().strftime("%Y%m%d%H%M%S"))

    # get message info
    sender_id = message_event["sender"]["id"]
    user_message = message_event["message"]["text"]
    print(f"[Webhook]: User [{sender_id}] ask", user_message, "at", current_time)

    # send typing indicator
    send_typing_indicator(sender_id)

    # random reponse delay
    delay = random.randint(1, 3)
    print(f"[Webhook]: delay {delay} seconds")

    # === Get reply from Gemini ===
    bot_reply = get_gemini_response(user_message, sender_id)
    delay = max(delay, len(bot_reply) / 30) # delay if the response is too long
    print("[Webhook]: reply", bot_reply[:100])

    # delay the rest 
    processing_time = int(datetime.now().strftime("%Y%m%d%H%M%S")) - current_time
    time.sleep(min(0, delay - processing_time))

    # === Send reply back to user ===
    send_facebook_message(sender_id, bot_reply)

@app.route("/test")
def test():
    return "Flask is working!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    print(request)
    if request.method == 'GET':
        # Webhook verification
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    elif request.method == 'POST':
        data = request.get_json()
        for entry in data.get("entry", []):
            for message_event in entry.get("messaging", []):
                object_type = data.get("object", "")
                print("[Webhook]: Received message from", object_type)
                if "message" in message_event and "text" in message_event["message"]:
                    handle_user_message(message_event)
        return "ok", 200

if __name__ == '__main__':
    app.run(port=3000)
