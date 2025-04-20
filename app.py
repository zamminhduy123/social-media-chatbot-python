from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai

# === Load environment variables ===
load_dotenv()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")

# === CONFIG ===
FACEBOOK_VERSION = 'v22.0'

# === Configure Gemini ===
genai.configure(api_key=API_KEY)
chat = genai.GenerativeModel("gemini-2.0-flash").start_chat()
app = Flask(__name__)


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
                sender_id = message_event["sender"]["id"]
                if "message" in message_event and "text" in message_event["message"]:
                    user_message = message_event["message"]["text"]
                    print("[Webhook]: User ask", user_message)

                    # === Get reply from Gemini ===
                    bot_reply = get_gemini_response(user_message)
                    print("[Webhook]: reply", bot_reply[:100])

                    # === Send reply back to user ===
                    send_facebook_message(sender_id, bot_reply)
        return "ok", 200


def get_gemini_response(user_message):
    try:
        response = chat.send_message(user_message)
        full_reply = ""
        for chunk in response:
            full_reply += chunk.text
        return full_reply
    except Exception as e:
        print("Gemini error:", e)
        return "Xin lỗi, mình chưa thể trả lời câu hỏi này."


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


@app.route("/test")
def test():
    return "Flask is working!"

if __name__ == '__main__':
    app.run(port=3000)