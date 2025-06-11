import os
from google.genai.types import (
    GenerateContentConfig,
    HarmBlockThreshold,
    HarmCategory,
    SafetySetting,
)
from pydantic import BaseModel

BASE_DIR = os.path.dirname(__file__)

HTML_GEMINI_CONFIG_FORM = ""
with open(f"{BASE_DIR}/pages/config.html", "r", encoding="utf8") as fhandle:
    HTML_GEMINI_CONFIG_FORM = fhandle.read()

SYSTEM_PROMPT = ""
with open(f"{BASE_DIR}/sale_system_prompt_test.txt", "r", encoding="utf8") as fhandle:
    SYSTEM_PROMPT = fhandle.read()

MODEL_ID = "gemini-2.0-flash"
TEMPERATURE = 0.0
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
    " được hỗ trợ tốt nhất nhé! 😳"
)

GREETING_RESPONSE = (
    "Chào bạn 👋 Mình là trợ lý ảo của KNI Institute, rất vui được hỗ trợ bạn."
    " Mình có thể giúp bạn tìm hiểu về TestAS, các khóa học luyện thi, hoặc tư vấn"
    " du học Đức."
    "\n\n"
    "Bạn có thể hỏi mình những câu hỏi như:\n"
    '- "TestAS là gì?"\n'
    '- "Luyện thi TestAS ở KNI có gì khác biệt?"\n'
    '- "Du học Đức cần chuẩn bị những gì?"'
    "\n\n"
    "Nếu bạn có góp ý gì cho mình, hãy dùng lệnh /feedback <tin nhắn> nhé. Cảm ơn bạn 🥰"
)


# Default value is not supported in the response schema for the Gemini API.
class BotMessage(BaseModel):
    message: str
    image_send_threshold: float
    image_urls: list[str]
    customer_name: str
    customer_phone_number: str
    customer_home_address: str
    customer_potential: float


def get_bot_message_defaults():
    return BotMessage(
        message="",
        image_send_threshold=0.0,
        image_urls=[],
        customer_name="",
        customer_phone_number="",
        customer_home_address="",
        customer_potential=0.0,
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


def get_chat_config_json() -> GenerateContentConfig:
    chat_config = get_chat_config()
    chat_config.response_mime_type = "application/json"
    chat_config.response_schema = BotMessage
    return chat_config
