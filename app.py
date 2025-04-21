from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

from gemini_prompt import MODEL_ID, PLACEHOLDER, get_chat_config
from google import genai

import random
from datetime import datetime, timedelta
import time
from collections import OrderedDict

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

SESSION_CAPACITY = 100
SESSION_TIME_THRESHOLD = 86400 # in second
chat_sessions = OrderedDict()

app = Flask(__name__)

# === === === === === === === ACTUAL WORK FUNCTION
def get_set_chat_sessions(sender_id):
    
    # create new chat session if sender is new.
    if sender_id not in chat_sessions:
        chat_sessions[sender_id] = {}
        chat_sessions[sender_id]["chat"] = client.chats.create(
            model=MODEL_ID,
            config=get_chat_config(),
        )

    # update chat session time to now
    current_time = datetime.now()
    chat_sessions[sender_id]["last_date"] = current_time

    # delete chat session if past certain threshold, user who triggers this is
    # one lucky bastard.
    sort_and_clean_chat_sessions(current_time)

    return chat_sessions[sender_id]

def sort_chat_sessions_by_date():
    # sort newest to oldest
    chat_sessions = OrderedDict(
        sorted(
            chat_sessions.items(),
            key=lambda item: item[1]["last_date"],
            reverse=False, # False: newest to oldest
        )
    )

def sort_and_clean_chat_sessions(current_time=None):
    current_time = current_time if current_time else datetime.now()

    sort_chat_sessions_by_date()

    # delete by capacity
    if len(chat_sessions) > SESSION_CAPACITY:
        n_session = len(chat_sessions) - SESSION_CAPACITY
        for _ in range(n_session):
            chat_sessions.popitem(last=True)

    # delete by time
    id_to_delete = set()
    for sender_id in reversed(chat_sessions):
        chat_session_date = chat_sessions[sender_id]["last_date"]
        if current_time - chat_session_date < timedelta(SESSION_TIME_THRESHOLD):
            id_to_delete.add(sender_id)
        else:
            # dict is ordered and sorted, break when there is no more session
            # past the time threshold.
            break
    
    for sender_id in id_to_delete:
        chat_sessions.pop(sender_id)


def get_gemini_response(user_message, sender_id):
    # actually generate response:
    try:
        chat_session = get_set_chat_sessions(sender_id)
        chat = chat_session["chat"]

        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        print("Gemini error:", e)
        return "Xin lỗi, mình chưa có thông tin về vấn đề này. Bạn vui lòng liên hệ trực tiếp với KNI qua số điện thoại +84 091-839-1099 hoặc email nhat@kni.vn để được hỗ trợ tốt nhất nhé! :blush:"

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
                if "message" in message_event and "text" in message_event["message"]:
                    handle_user_message(message_event)
        return "ok", 200

if __name__ == '__main__':
    app.run(port=3000)
