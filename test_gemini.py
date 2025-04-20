import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=API_KEY)

models = genai.list_models()
for m in models:
    print(f"{m.name} - {m.supported_generation_methods}")

# Start chat session
chat = genai.GenerativeModel("gemini-2.0-flash").start_chat()

# Get user input
user_input = input("Bạn muốn hỏi Gemini điều gì? ")

# Send message
try:
    response = chat.send_message(user_input)
    print("\n🤖 Gemini trả lời:")
    print(response.text)
except Exception as e:
    print("Lỗi khi gọi Gemini:", e)