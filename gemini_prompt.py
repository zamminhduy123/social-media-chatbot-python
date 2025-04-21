import os
from google.genai import types


SYSTEM_PROMPT = ""
with open("system_prompt.txt","r", encoding="utf8") as fhandle:
    SYSTEM_PROMPT = fhandle.read()

MODEL_ID = "gemini-2.0-flash"
TEMPERATURE=0
TOP_P=0.95
TOP_K=10
CANDIDATE_COUNT=1
SEED=5

PLACEHOLDER = """Chào bạn! Mình là chatbot hỗ trợ của KNI Education, rất vui
được hỗ trợ bạn. Bạn có câu hỏi nào về luyện thi TestAS hay tư vấn du học Đức
không? Mình sẽ cố gắng trả lời một cách chi tiết và đầy đủ nhất có thể! 😊"""

# === GenerateContentConfig ===
def get_chat_config():
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        candidate_count=CANDIDATE_COUNT,
        seed=SEED,
    )