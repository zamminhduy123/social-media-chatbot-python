import os
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, render_template_string, request
from google import genai
from google.genai import types as genai_types
from google.genai.chats import Chat

from api import meta as meta_api
from controller.ContextController import ContextController
from controller.FeedbackController import FeedbackController
from controller.SessionController import SessionController
from controller.DebounceMessageController import DebounceMessageController, Message
from controller.utils.chat import clean_message, convert_to_gemini_chat_history
from gemini_prompt import (
    DEFAULT_RESPONSE,
    HTML_GEMINI_CONFIG_FORM,
    SEED,
    SYSTEM_PROMPT,
    TEMPERATURE,
    BotMessage,
    get_chat_config_json,
)
from script.RAG import text_chunking
from utils import logging, thread_utils
import json

# === Load environment variables ===
load_dotenv()
db_path = os.getenv("CHROMA_DB_PATH", "chroma_db")
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
    INSTA_URL,
    MESSAGE_OBJECT_TYPE,
    NUM_MESSAGE_CONTEXT,
    RESUME_BOT_KEYWORD,
    DEBOUNCE_TIME,
    BOT_TYPING_CPM,
    IMAGE_SEND_KEYWORD,
    COLLECTION_NAME
)

# === Configure Gemini ===
# Configure Gemini
client = genai.Client(api_key=API_KEY)

CONFIG_FIELD_TYPE_MAP = {
    "gemini_system_instruction": (str, SYSTEM_PROMPT),
    "gemini_temperature": (float, TEMPERATURE),
    "gemini_max_output_tokens": (int, 2000),
    "gemini_seed": (int, SEED),
    "app_bot_typing_cpm": (int, BOT_TYPING_CPM),
    "app_debounce_time": (float, DEBOUNCE_TIME),
}

g_gemini_config = get_chat_config_json().model_dump(mode="python", exclude_unset=True)
g_app_config = {"bot_typing_cpm": BOT_TYPING_CPM,
                "debounce_time": DEBOUNCE_TIME}

app = Flask(__name__)

chat_sessions = SessionController(client, default_gemini_config=g_gemini_config)
feedback_controller = FeedbackController(delta_time=0) # for testing, change to 30 for production
debounce_controller = DebounceMessageController(wait_seconds=DEBOUNCE_TIME) # 5 for testing, change to 10 for production

# Global context controller
context_controller = ContextController(path=db_path, collection_name=COLLECTION_NAME)

tools = [
    {
        "function_declarations": [
            {
                "name": "retrieve_testas_information",
                "description": "Use this function when the user asks a specific question about the TestAS exam, German universities, requirements, dates, structure, or any factual topic.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "The specific question the user is asking."
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    }
]

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
        return clean_message(response.text) # type: ignore
    except Exception as e:
        print("Gemini error:", e)
        return DEFAULT_RESPONSE


def get_gemini_response_with_context_json(
    user_message: str,
    context: str,
    sender_id: str,
    history: List[genai_types.Content] = None,
    config: Dict = None,
) -> BotMessage | None:
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
    return get_gemini_response_json(message, sender_id, history, config)

def get_gemini_response_with_context_json_rag(
    user_message: str,
    context: str,
    sender_id: str,
    history: List[genai_types.Content] = None,
    config: Dict = None,
) -> BotMessage | None:
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

    results = context_controller.query_relavant(user_message)
    # 3. Prepare the context for the LLM
    context = "\n---\n".join(results['documents'][0]) if results and results.get('documents') else "No relevant context found."

    message = f"""
    Dựa trên ngữ cảnh sau, vui lòng trả lời câu hỏi của người dùng. Nếu ngữ cảnh không chứa câu trả lời, hãy nói rằng bạn không biết.

    Ngữ cảnh:
    {context}

    Câu hỏi: {user_message}

    Trả lời:
    """
    return get_gemini_response_json(message, sender_id, history, config)

def get_gemini_response_json(
    user_message: str,
    sender_id: str,
    history: List[genai_types.Content] = None,
    config: Dict = None,
) -> BotMessage | None:
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
        chat_session = chat_sessions.get_session(sender_id, history, tools=tools)
        if chat_session == None:
            return None

        if config:
            config = genai_types.GenerateContentConfig(**config)

        chat: Chat = chat_session["chat"]  # type: ignore
        _response = chat.send_message(user_message, config=config)

        # Check if the model decided to call a function
        try:
            function_call = _response.candidates[0].content.parts[0].function_call
            # If we are here, the model chose a tool. Now we execute it.
            if function_call.name == "retrieve_testas_information":
                query_arg = function_call.args['query']
                _response.text = get_gemini_response_with_context_json_rag(query=query_arg)
                print(f"-> Final Answer: {_response.text}")
        except (IndexError, AttributeError):
            # The model decided to answer directly without using a tool
            print("\n[Decision: Direct Answer (No Tool)]")
            print(f"-> Model Response: {_response.text}")

        response = BotMessage(
            message=clean_message(_response.text),
            image_send_threshold=0.0,
            image_urls=[],
            customer_potential=0.0,
        )
        if _response.parsed:
            response: BotMessage = _response.parsed
            response.message = clean_message(response.message)
        return response  # type: ignore
    except Exception as e:
        print("Gemini error:", e)
        return BotMessage(
            message=DEFAULT_RESPONSE,
            image_send_threshold=0.0,
            image_urls=[],
            customer_potential=0.0,
        )


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

def get_conversation_label(sender_id, object_type):
    conversation = meta_api.get_conversation_messages_by_user_id(sender_id)
    if not conversation:
        return ""
    
    # Get the labels of the conversation
    labels = meta_api.get_labels_of_conversation(sender_id, object_type)
    print("[Webhook]: Conversation labels", labels)
    if not labels:
        return ""
    # Return the first label
    return labels[0] if labels else ""

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


# ===== === === === === === === CORE LOGICS
def get_and_send_message(sender_id, messages : Message, object_type):
    print("[Webhook]: Get and send message", sender_id, messages)
    # send typing indicator
    meta_api.send_typing_indicator(sender_id)

    # get message info 
    reply_context, full_user_message = [], []
    for message in messages:
        if (message.get('reply_to', None) != None):
            reply_context.append(message['reply_to'])
        full_user_message.append(message['text'])
    user_message = "\n".join(full_user_message)
    reply_context = "\n".join(reply_context) if (reply_context) else None
    print(f"[Webhook]: User [{sender_id}] ask", user_message, "with reply context", reply_context)

    # === Get reply from Gemini ===

    # fetch chat history if session does not exist
    chat_history = None
    if not chat_sessions.is_session_exist(sender_id):
        batch_messages = get_new_conversation_context(sender_id, object_type)
        if batch_messages:
            chat_history = convert_to_gemini_chat_history(batch_messages)
            print("[Webhook]: New conversation context", len(batch_messages))

    # handle reply if any
    if reply_context:
        print("[Webhook]: Reply to message", reply_context)    
        bot_response = get_gemini_response_with_context_json(
            user_message,
            reply_context,
            sender_id,
            history=chat_history,
            config=g_gemini_config,
        )

    else:
        bot_response = get_gemini_response_json(
            user_message,
            sender_id,
            history=chat_history,
            config=g_gemini_config,
        )

    if not bot_response:
        # Suspended, no response
        return

    # Bot response may contain more than one message.
    bot_reply = bot_response.message
    image_send_threshold = bot_response.image_send_threshold
    image_urls = bot_response.image_urls
    print("[Webhook]: reply", bot_reply[:100])

    
    # assume typing cost 190 char per minute 
    typing_time = len(bot_reply) / g_app_config["bot_typing_cpm"] * 60  
    print("[Webhook]: Bot Reply", bot_reply)

    if bot_reply:
        thread_utils.delayed_call(typing_time, meta_api.send_meta_message, sender_id, bot_reply, object_type)
    # TODO: might want to add this threshold into a config
    # also image_urls may contains multiple urls (should be up to 5)
    # NOTE: `image_send_threshold` can be above 0.5 without any image_urls. 
    if image_urls and image_send_threshold > 0.5: 
        image_url = image_urls[0]
        print("[Webhook]: Image URL send", image_url)
        image_url = f"https://{image_url}" if not image_url.startswith("http") else image_url
        # extra delay for image
        thread_utils.delayed_call(typing_time, meta_api.send_meta_image, sender_id, image_url, object_type=object_type)

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
    
    if user_message.lower().startswith("/dev-no-history"):
        # delete current chat session with sender and initialize a new chat session without history.
        chat_sessions.delete_session(sender_id)
        chat_sessions.create_session(sender_id)
        print(f"[Webhook]: Chat session reset with no history for {sender_id}")
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

    # get user conversation label
    get_labels_of_conversation = get_conversation_label(sender_id, object_type)

    # get reply if exists
    reply, reply_message_text = message_event.get("message", {}).get("reply_to", None), None
    if reply != None:
        # reply to a message
        message_id = reply["mid"]
        reply_message_text = meta_api.get_message_by_id(message_id, object_type)

    def debounce_callback(uid, msgs):
        # get and send message
        print("[Webhook]: Debounce callback", uid, msgs)
        if (msgs):
            # get and send message
            get_and_send_message(uid, msgs, object_type)
        else:
            print("[Webhook]: No messages in debounce buffer")
   
    debounce_controller.add_message(
        sender_id,
        {
            "text": user_message,
            "reply_to": reply_message_text,
        },
        debounce_callback
    )

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

@app.route("/config", methods=["GET", "POST"])
def config():
    def _safe_cast(val, to_type, default):
        try:
            return to_type(val)
        except (ValueError, TypeError):
            return default

    def _apply_app_config():
        try:
            debounce_time = max(0.0, g_app_config["debounce_time"])
            debounce_controller.wait_seconds=debounce_time
            return True
        except Exception as e:
            print(f"[Config] error changing app config - {e}")
            return False

    if request.method == "POST":
        form = request.form
        for key in form:
            field_value = form.get(key, "")
            field_type, field_default = CONFIG_FIELD_TYPE_MAP[key]
            field_value = _safe_cast(field_value, field_type, field_default)
            if key.startswith("gemini_"):
                key = key.removeprefix("gemini_")
                g_gemini_config[key] = field_value
            elif key.startswith("app_"):
                key = key.removeprefix("app_")
                g_app_config[key] = field_value

        success = _apply_app_config()
        if success:
            print(f"[Config] Successfully change config.")

    context = {**g_gemini_config, **g_app_config}
    return render_template_string(HTML_GEMINI_CONFIG_FORM, **context)

@app.route("/htop/<int:interval>")
def htop(interval:int):
    log = logging.get_system_usage(interval)
    return log

@app.route("/reset_session")
def reset():
    # Reset all sessions
    chat_sessions.hard_reset()
    return "Reset all sessions"

@app.route("/update_context", methods=["POST"])
def update_context():
    """
    Updates the context repository with data from an uploaded JSON file.
    The JSON file should contain a list of strings.
    """
    if 'file' not in request.files:
        return "No file part in the request", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected for uploading", 400
    if file and file.filename.endswith('.json'):
        try:
            # Read the content of the file
            content = file.read()
            data = json.loads(content)

            # Assuming the JSON file contains a list of documents (strings)
            if not isinstance(data, list):
                return "JSON file must contain a list of documents.", 400

            # Add documents to the repository
            all_chunks = text_chunking(data)
            context_controller.add_documents(
                documents=[chunk['content'] for chunk in all_chunks],
                metadatas=[{'source_url': chunk['source_url'], 'title': chunk['title'], 'chunk_id': chunk['chunk_id']} for chunk in all_chunks]
            )

            return f"Successfully added {len(data)} documents to the repository.", 200
        except json.JSONDecodeError:
            return "Invalid JSON format.", 400
        except Exception as e:
            print(f"Error updating context: {e}")
            return "An error occurred while updating the context.", 500
    else:
        return "Invalid file type. Please upload a JSON file.", 400

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
