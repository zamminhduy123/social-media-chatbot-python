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
INSTA_ACCESS_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")

# === CONFIG ===
from constant import MESSAGE_OBJECT_TYPE, FACEBOOK_URL, INSTA_URL

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
    url = f"{FACEBOOK_URL['message']}?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "sender_action": "typing_on"
    }
    headers = {'Content-Type': 'application/json'}
    requests.post(url, headers=headers, json=payload)

def send_meta_message(
        psid, 
        message, 
        message_object=MESSAGE_OBJECT_TYPE["facebook_page"]
):
    url = f"{FACEBOOK_URL['message']}?access_token={PAGE_ACCESS_TOKEN}"
    if (message_object == MESSAGE_OBJECT_TYPE["instagram"]):
        url = f"{INSTA_URL['message']}?access_token={INSTA_ACCESS_TOKEN}"
                                                                            
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
def handle_user_message(message_event, object_type):
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
    send_meta_message(sender_id, bot_reply, object_type)

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
                    handle_user_message(message_event, object_type)
        return "ok", 200

if __name__ == '__main__':
    app.run(port=3000)
