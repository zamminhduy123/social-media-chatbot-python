from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
from google import genai
from google.genai.chats import Chat

import random
from datetime import datetime
import time

from controller.SessionController import SessionController
from controller.FeedbackController import FeedbackController
from gemini_prompt import DEFAULT_RESPONSE

# === Load environment variables ===
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
INSTA_ACCESS_TOKEN = os.getenv("INSTA_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
INSTA_ID = os.getenv("INSTA_ID")
API_KEY = os.getenv("GEMINI_API_KEY")
APP_ID = os.getenv("APP_ID")

# === CONFIG ===
from constant import MESSAGE_OBJECT_TYPE, FACEBOOK_URL, INSTA_URL, RESUME_BOT_KEYWORD

# === Configure Gemini ===
# Configure Gemini
client = genai.Client(api_key=API_KEY)

app = Flask(__name__)

chat_sessions = SessionController(client)
feedback_controller = FeedbackController(delta_time=0) # for testing, change to 30 for production

# === === === === === === === ACTUAL WORK FUNCTION
def get_gemini_response(user_message, sender_id) -> str:
    # actually generate response:
    try:
        chat_session = chat_sessions.get_session(sender_id)
        if (chat_session == None):
            return None
        chat: Chat = chat_session["chat"] # type: ignore
        response = chat.send_message(user_message)
        return response.text # type: ignore
    except Exception as e:
        print("Gemini error:", e)
        return DEFAULT_RESPONSE

def send_typing_indicator(psid, platform=MESSAGE_OBJECT_TYPE["facebook_page"]):
    url = f"{FACEBOOK_URL['typing']}?access_token={PAGE_ACCESS_TOKEN}"
    if (platform == MESSAGE_OBJECT_TYPE["instagram"]):
        url = f"{INSTA_URL['typing']}?access_token={INSTA_ACCESS_TOKEN}"
    
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

def get_message_by_id(message_id, message_object=MESSAGE_OBJECT_TYPE["facebook_page"]):
    url = f"{FACEBOOK_URL['base']}/{message_id}?fields=message&access_token={PAGE_ACCESS_TOKEN}"
    if message_object == MESSAGE_OBJECT_TYPE["instagram"]:
        url = f"{INSTA_URL['base']}/{message_id}?fields=message&access_token={INSTA_ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.get(url, headers=headers)
        if response.ok:
            data = response.json()
            return data.get("message")
        else:
            print("Error fetching message:", response.text)
            return ""
    except Exception as e:
        print("Exception fetching message:", e)
        return ""
    
def check_owner(object_type, sender_id):
    print("[Webhook]: Check owner", sender_id)
    if object_type == MESSAGE_OBJECT_TYPE["facebook_page"]:
        return sender_id == PAGE_ID
    elif object_type == MESSAGE_OBJECT_TYPE["instagram"]:
        return sender_id == INSTA_ID
    return False

def is_bot_message(app_id, sender_id, object_type):
    if (check_owner(object_type, sender_id) and str(app_id) == str(APP_ID)):
        return True
    return False
# === === === === === === === ROUTING FUNCTION
def handle_user_feedback(sender_id, user_message, object_type):
    feedback_text = user_message[len("/feedback"):].strip()
    feedback_controller.log_feedback_text(object_type, sender_id, feedback_text)
    send_meta_message(sender_id, "Cảm ơn bạn đã góp ý! 💬", object_type) # ✅ 

def handle_user_message(message_event, object_type):
    # get time 
    current_time = int(datetime.now().strftime("%Y%m%d%H%M%S"))

    # get message info
    sender_id = message_event["sender"]["id"]
    user_message = message_event["message"]["text"]
    print(f"[Webhook]: User [{sender_id}] ask", user_message, "at", current_time)

    # handle user feedback
    if user_message.lower().startswith("/feedback"):
        #STOP, no Gemini reply
        handle_user_feedback(sender_id, user_message, object_type)
        return
    
    if (chat_sessions.is_chat_suspended(sender_id)):
        # suspended, no response
        print("[Webhook]: Chat session suspended for user", sender_id)
        return
    
    # owner take over
    if check_owner(object_type, sender_id):
        recipient_id = message_event["recipient"]['id']
        # suspen chat session
        print("[Webhook]: Owner take over conversation", recipient_id)
        chat_sessions.suspend_session(recipient_id)

        if (RESUME_BOT_KEYWORD in user_message.lower()):
            # resume chat session
            print("[Webhook]: Owner resume chat session", recipient_id)
            chat_sessions.resume_session(recipient_id)
        return
    
    # send typing indicator
    send_typing_indicator(sender_id)

    # random reponse delay
    delay = random.randint(1, 3)
    print(f"[Webhook]: delay {delay} seconds")

    # === Get reply from Gemini ===
    bot_reply = get_gemini_response(user_message, sender_id)
    if (bot_reply == None):
        # Suspended, no response
        return
    delay = max(delay, len(bot_reply) / 30) # delay if the response is too long
    print("[Webhook]: reply", bot_reply[:100])

    # delay the rest 
    processing_time = int(datetime.now().strftime("%Y%m%d%H%M%S")) - current_time
    time.sleep(max(0, delay - processing_time))

    # === Send reply back to user ===
    send_meta_message(sender_id, bot_reply, object_type)

def handle_reaction_event(event, object_type):
    print("[Webhook]: Reaction event", event)
    sender_id = event["sender"]["id"]
    message_id = event["reaction"]["mid"]
    action = event["reaction"]["action"]

    # try get message by id
    message = get_message_by_id(message_id, object_type)

    if action == "react":
        reaction_type = event["reaction"]["reaction"]
        emoji = event["reaction"]["emoji"]
        # Reaction added
        feedback_controller.log_feedback(object_type, sender_id, message_id, message, reaction_type, emoji)
    elif action == "unreact":
        # Reaction removed
        feedback_controller.remove_feedback(message_id)

@app.route("/test")
def test():
    return "Flask is working!"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # print(request)
    if request.method == 'GET':
        # Webhook verification
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    elif request.method == 'POST':
        data = request.get_json()
        print("[Webhook]: Received data:", data)
        for entry in data.get("entry", []):
            for message_event in entry.get("messaging", []):
                if "message" in message_event:
                    object_type = data.get("object", "")
                    sender_id = message_event["sender"]["id"]
                    message = message_event.get("message", {})
                    app_id = message.get("app_id", "")
                    is_echo = message.get("is_echo", False)
                    
                    print("[Webhook]: Received message from", sender_id, "app_id:", app_id, "is_echo:", is_echo, "in", object_type, is_bot_message(app_id, sender_id, object_type))
                    
                    #check is bot message
                    if (is_bot_message(app_id, sender_id, object_type) and is_echo == True):
                        print("[Webhook]: Bot message, ignore")
                    elif "text" in message_event["message"]:
                        handle_user_message(message_event, object_type)
                    elif "reaction" in message_event:
                        handle_reaction_event(message_event, object_type)
        return "ok", 200

if __name__ == '__main__':
    app.run(port=3000)
