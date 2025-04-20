from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

from gemini_prompt import MODEL_ID, PLACEHOLDER, get_chat_config
from google import genai

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
client = genai.Client(api_key=API_KEY)

# models = genai.list_models()
# for m in models:
#     print(f"{m.name} - {m.supported_generation_methods}")

chat = client.chats.create(
    model=MODEL_ID,
    config=get_chat_config(),
)

# Get user input
user_input = input("Bạn muốn hỏi Gemini điều gì? ")

# Send message
try:
    response = chat.send_message(user_input)
    print("\n🤖 Gemini trả lời:")
    print(response.text)
except Exception as e:
    print("Lỗi khi gọi Gemini:", e)