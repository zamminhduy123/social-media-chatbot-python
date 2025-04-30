import os
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)

BASE_DIR = os.path.dirname(__file__)

SYSTEM_PROMPT = ""
with open(f"{BASE_DIR}/system_prompt.txt", "r", encoding="utf8") as fhandle:
    SYSTEM_PROMPT = fhandle.read()

MODEL_ID = "gemini-2.0-flash"
TEMPERATURE = 0
TOP_P = 0.95
TOP_K = 10
CANDIDATE_COUNT = 1
SEED = 5

PLACEHOLDER = (
    "Chào bạn! Mình là chatbot hỗ trợ của KNI Education, rất vui được hỗ trợ"
    " bạn. Bạn có câu hỏi nào về luyện thi TestAS hay tư vấn du học Đức không?"
    " Mình sẽ cố gắng trả lời một cách chi tiết và đầy đủ nhất có thể! 😊"
)

DEFAULT_RESPONSE = (
    "Xin lỗi, mình chưa có thông tin về vấn đề này. Bạn vui lòng liên hệ trực"
    " tiếp với KNI qua số điện thoại +84 091-839-1099 hoặc email nhat@kni.vn để"
    " được hỗ trợ tốt nhất nhé! :blush:"
)


# === GenerateContentConfig ===
def get_chat_config():
    return GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        candidate_count=CANDIDATE_COUNT,
        seed=SEED,
        safety_settings=[
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
        ],
    )

def get_evaluator_config():
    return GenerateContentConfig(
        temperature=TEMPERATURE,
        top_p=1,
        top_k=0,
        candidate_count=CANDIDATE_COUNT,
        seed=42,
        safety_settings=[
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,  # Block most
            ),
        ],
    )
