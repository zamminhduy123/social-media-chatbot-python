from typing import List, Tuple

from google import genai
from google.genai import types as genai_types

from api import meta as meta_api


def convert_to_gemini_chat_history(batch_messages: List[Tuple[str,str]]) ->List[genai_types.Content]:
    chat_history = []
    for sender_id, message in batch_messages:
        role = None
        if sender_id:
            role = "model" if sender_id == meta_api.PAGE_ID else "user"
        # handle role=None
        else:
            role = "user"
            message = f'Context: """{message}"""'

        chat_history.append(
            genai_types.Content(parts=[genai_types.Part(text=message)], role=role)
        )
    
    # first message must be from `user`
    if chat_history[0].role != "user":
        first_message = chat_history[0].parts[0].text
        first_message = f'Context: """owner: {first_message}"""'
        chat_history[0].role = "user"
    return chat_history
