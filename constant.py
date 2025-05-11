FACEBOOK_VERSION = 'v22.0'
FACEBOOK_BASE_URL = f"https://graph.facebook.com/{FACEBOOK_VERSION}"
FACEBOOK_URL = {
    'base': FACEBOOK_BASE_URL,
    'message': f"{FACEBOOK_BASE_URL}/me/messages",
    'typing': f"{FACEBOOK_BASE_URL}/me/messages",
    'conversation_message': f"{FACEBOOK_BASE_URL}/me/conversations",
}

INSTA_VERSION = 'v22.0'
INSTAGRAM_BASE_URL = f"https://graph.instagram.com/{INSTA_VERSION}"
INSTA_URL = {
    'base': INSTAGRAM_BASE_URL,
    'message': f"{INSTAGRAM_BASE_URL}/me/messages",
    'typing': f"{FACEBOOK_BASE_URL}/me/messages",
}

MESSAGE_OBJECT_TYPE = {
    'instagram': 'instagram',
    'facebook_page': 'page'
}

RESUME_BOT_KEYWORD = "!!!"
NUM_MESSAGE_CONTEXT = 10
DEBOUNCE_TIME = 20