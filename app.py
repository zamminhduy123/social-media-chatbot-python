import os
import random
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, render_template_string, request
from google import genai
from google.genai import types as genai_types
from google.genai.chats import Chat

from api import meta as meta_api
from controller.FeedbackController import FeedbackController
from controller.SessionController import SessionController
from controller.utils.chat import convert_to_gemini_chat_history
from gemini_prompt import DEFAULT_RESPONSE, SYSTEM_PROMPT
from utils import logging, thread_utils

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
from constant import (
    FACEBOOK_URL,
    HTML_GEMINI_CONFIG_FORM,
    INSTA_URL,
    MESSAGE_OBJECT_TYPE,
    NUM_MESSAGE_CONTEXT,
    RESUME_BOT_KEYWORD,
)

# === Configure Gemini ===
# Configure Gemini
client = genai.Client(api_key=API_KEY)
g_gemini_config = {"system_instruction": SYSTEM_PROMPT}

app = Flask(__name__)

chat_sessions = SessionController(client)
feedback_controller = FeedbackController(delta_time=0) # for testing, change to 30 for production


# === === === === === === === ACTUAL WORK FUNCTION
def get_gemini_response_with_context(
    user_message: str,
    context: str,
    sender_id: str,
    history: List[genai_types.Content] = None,
    config: Dict = None,
) -> str:
    """
    Generates a Gemini response using additional context prepended to the user message.

    :param user_message: The user's input to the chatbot.
    :param context: Supplementary context to guide the model's response.
    :param sender_id: Unique identifier used to retrieve or create a chat session.
    :param history: Optional list of past messages (chat history) for context.
    :param system_prompt: Optional instruction to condition the model's response
        style or behavior, this will override the configuration of the chat session.
    :return: The model's generated text reply, or a fallback message on error.
    """
    message = f'Context: """{context}"""\n\n{user_message}'
    return get_gemini_response(message, sender_id, history, config)


def get_gemini_response(
    user_message: str,
    sender_id: str,
    history: List[genai_types.Content] = None,
    config: Dict = None,
) -> str:
    """
    Generates a Gemini response based on the user message and optional session data.

    :param user_message: The user's input to the chatbot.
    :param sender_id: Unique identifier used to retrieve or create a chat session.
    :param history: Optional list of past messages (chat history) for context.
    :param system_prompt: Optional instruction to condition the model's response
        style or behavior, this will override the configuration of the chat session.
    :return: The model's generated text reply, or a fallback message on error.
    """
    # actually generate response:
    try:
        chat_session = chat_sessions.get_session(sender_id, history)
        if chat_session == None:
            return None

        if config:
            config = genai_types.GenerateContentConfig(**config)
            
        chat: Chat = chat_session["chat"]  # type: ignore
        response = chat.send_message(user_message, config=config)
        return response.text  # type: ignore
    except Exception as e:
        print("Gemini error:", e)
        return DEFAULT_RESPONSE


def get_new_conversation_context(sender_id, object_type):
    """
    Get the context of a new conversation with a user.
    """
    # Get all messages between the page and the user
    conversation = meta_api.get_conversation_messages_by_user_id(sender_id)
    if not conversation:
        return ""

    last_5_messages = conversation[:NUM_MESSAGE_CONTEXT]
    message_ids = [msg["id"] for msg in last_5_messages]
    
    # Batch fetch the messages by IDs
    batch_messages = meta_api.batch_get_messages_by_ids_v2(message_ids, object_type)
    
    return batch_messages

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
    meta_api.send_meta_message(sender_id, "Cảm ơn bạn đã góp ý! 💬", object_type) # ✅ 

def handle_user_message(message_event, object_type):
    # get time
    current_time = int(datetime.now().strftime("%Y%m%d%H%M%S"))

    # get message info
    sender_id = message_event["sender"]["id"]
    user_message = message_event["message"]["text"]
    print(f"[Webhook]: User [{sender_id}] ask", user_message, "at", current_time)

    # handle user feedback
    if user_message.lower().startswith("/feedback"):
        # STOP, no Gemini reply
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
    meta_api.send_typing_indicator(sender_id)

    delay_time = random.randint(1, 3)
    def get_and_set_message():
        # handle reply if exist
        bot_reply = None
        reply = message_event["message"].get("reply_to", None)
        print(f"[Webhook]: user reply_to: {reply} - type: {type(reply)}")
        # === Get reply from Gemini ===

        # fetch chat history if session does not exist
        chat_history = None
        if not chat_sessions.is_session_exist(sender_id):
            batch_messages = get_new_conversation_context(sender_id, object_type)
            if batch_messages:
                chat_history = convert_to_gemini_chat_history(batch_messages)
                print("[Webhook]: New conversation context", len(batch_messages))

        # handle reply if any
        if reply:
            # reply to a message
            message_id = reply["mid"]
            reply_message_text = meta_api.get_message_by_id(message_id, object_type)
            print("[Webhook]: Reply to message", reply_message_text)    
            bot_reply = get_gemini_response_with_context(
                user_message,
                reply_message_text,
                sender_id,
                history=chat_history,
                config=g_gemini_config,
            )

        else:
            bot_reply = get_gemini_response(
                user_message,
                sender_id,
                history=chat_history,
                config=g_gemini_config,
            )

        if not bot_reply:
            # Suspended, no response
            return
        print("[Webhook]: reply", bot_reply[:100])

        meta_api.send_meta_message(sender_id, bot_reply, object_type)

    print(f"[Webhook]: Delay time: {delay_time} seconds")
    thread_utils.delayed_call(0, get_and_set_message) # 0 for testing, change to delay_time for production

def handle_reaction_event(event, object_type):
    print("[Webhook]: Reaction event", event)
    sender_id = event["sender"]["id"]
    message_id = event["reaction"]["mid"]
    action = event["reaction"]["action"]

    # try get message by id
    message = meta_api.get_message_by_id(message_id, object_type)

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

@app.route("/gemini_config", methods=["GET", "POST"])
def gemini_config():
    if request.method == "POST":
        new_value = request.form.get("input_value", "")
        g_gemini_config["system_instruction"] = new_value  # Update variable

    return render_template_string(HTML_GEMINI_CONFIG_FORM, value=g_gemini_config["system_instruction"])

@app.route("/htop/<int:interval>")
def htop(interval:int):
    log = logging.get_system_usage(interval)
    return log

@app.route("/reset_session")
def reset():
    # Reset all sessions
    chat_sessions.hard_reset()
    return "Reset all sessions"

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
        object_type = data.get("object", "")
        print("================================")
        print("[Webhook]: Received data:", data)
        print(f"[GLOBAL] Chat sessions: {list(chat_sessions.sessions.keys())}")
        print(f"[GLOBAL] Suspended Sessions: {list(chat_sessions.suspended_sessions.keys())}")
        for entry in data.get("entry", []):
            for message_event in entry.get("messaging", []):
                if "message" in message_event:
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
        
        print("[Webhook]: Finished processing")
        return "ok", 200

if __name__ == '__main__':
    app.run(port=3000)
