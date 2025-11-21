import httpx
import os
from dotenv import load_dotenv
import json
from gemini_prompt import DEFAULT_RESPONSE
import mimetypes
from io import BytesIO

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
from constant import MESSAGE_OBJECT_TYPE, FACEBOOK_URL, INSTA_URL, RESUME_BOT_KEYWORD, NUM_MESSAGE_CONTEXT, IMAGE_ATTACHMENT_TYPE

async def get_message_by_id(message_id, message_object=MESSAGE_OBJECT_TYPE["facebook_page"]):
    url = f"{FACEBOOK_URL['base']}/{message_id}?fields=message&access_token={PAGE_ACCESS_TOKEN}"
    if message_object == MESSAGE_OBJECT_TYPE["instagram"]:
        url = f"{INSTA_URL['base']}/{message_id}?fields=message&access_token={INSTA_ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("message")
            else:
                print("Error fetching message:", response.text)
                return ""
    except Exception as e:
        print("Exception fetching message:", e)
        return ""

async def get_conversation_messages_by_user_id(user_id):
    """
    Get all messages between the page and a specific user_id (PSID).
    """
    url = f"{FACEBOOK_URL['conversation_message']}?fields=participants&access_token={PAGE_ACCESS_TOKEN}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                conversations = response.json().get("data", [])
                for convo in conversations:
                    participants = convo.get("participants", {}).get("data", [])
                    participant_ids = [p["id"] for p in participants]
                    if user_id in participant_ids:
                        convo_id = convo["id"]
                        # Found the conversation with this user
                        messages_url = f"{FACEBOOK_URL['base']}/{convo_id}/messages?access_token={PAGE_ACCESS_TOKEN}"
                        msg_response = await client.get(messages_url)
                        if msg_response.status_code == 200:
                            return msg_response.json().get("data", [])
                        else:
                            print("rror fetching messages:", msg_response.text)
                            return []
            else:
                print("Error fetching conversations:", response.text)
                return []
    except Exception as e:
        print("Exception during conversation fetch:", e)
        return []

async def batch_get_messages_by_ids(message_ids, object_type=MESSAGE_OBJECT_TYPE["facebook_page"]):
    batch = []
    access_token = PAGE_ACCESS_TOKEN if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else INSTA_ACCESS_TOKEN

    for msg_id in message_ids:
        batch.append({
            "method": "GET",
            "relative_url": f"{msg_id}?fields=message"
        })

    url = FACEBOOK_URL['base'] if (object_type == MESSAGE_OBJECT_TYPE["facebook_page"]) else INSTA_URL['base']
    headers = {'Content-Type': 'application/json'}
    payload = {
        "access_token": access_token,
        "batch": batch
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                results = response.json()
                messages = []
                for item in results:
                    body = json.loads(item.get("body", "{}"))
                    messages.append(body.get("message", ""))
                return messages
            else:
                print("Batch fetch error:", response.text)
                return []
    except Exception as e:
        print("Exception during batch message fetch:", e)
        return []


async def batch_get_messages_by_ids_v2(message_ids, object_type=MESSAGE_OBJECT_TYPE["facebook_page"]):
    batch = []
    access_token = PAGE_ACCESS_TOKEN if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else INSTA_ACCESS_TOKEN

    for msg_id in message_ids:
        batch.append({
            "method": "GET",
            "relative_url": f"{msg_id}?fields=message,from"
        })

    url = FACEBOOK_URL['base'] if (object_type == MESSAGE_OBJECT_TYPE["facebook_page"]) else INSTA_URL['base']
    headers = {'Content-Type': 'application/json'}
    payload = {
        "access_token": access_token,
        "batch": batch
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                results = response.json()
                messages = []
                for item in results:
                    body: dict = json.loads(item.get("body", "{}"))
                    sender_id = body.get("from", {}).get("id", None)
                    message = body.get("message", "")
                    messages.append((sender_id, message))
                return messages
            else:
                print("Batch fetch error:", response.text)
                return []
    except Exception as e:
        print("Exception during batch message fetch:", e)
        return []

async def _upload_image_get_attachment_id(image_source: str,
                                    source_type: str,
                                    object_type=MESSAGE_OBJECT_TYPE["facebook_page"]):
    """
    Uploads an image to Facebook and returns the attachment ID.
    If the source_type is 'url', returns None as no upload is necessary.
    """
    if source_type == IMAGE_ATTACHMENT_TYPE["url"]:
        return None
    access_token = os.getenv("PAGE_ACCESS_TOKEN") if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else os.getenv("INSTA_ACCESS_TOKEN")
    page_id = os.getenv("PAGE_ID") if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else os.getenv("INSTA_ID")

    url = f"{FACEBOOK_URL['base']}/{page_id}/message_attachments"

    mime_type, _ = mimetypes.guess_type(image_source)
    mime_type = mime_type or "image/jpeg"

    payload = {
        "is_reusable": False
    }
    if (source_type == IMAGE_ATTACHMENT_TYPE["url"]):
        payload["url"] = image_source

    try:
        async with httpx.AsyncClient() as client:
            if (source_type == IMAGE_ATTACHMENT_TYPE["file"]):
                with open(image_source, "rb") as image_file:
                    files = {
                        'filedata': (os.path.basename(image_source), image_file, mime_type)
                    }
                    data = {
                        'message': json.dumps({
                            'attachment': {
                                'type': 'image',
                                'payload': payload
                            }
                        }),
                        'access_token': access_token
                    }
                    response = await client.post(url, files=files, data=data)
            else:
                data = {
                    'message': json.dumps({
                        'attachment': {
                            'type': 'image',
                            'payload': payload
                        }
                    }),
                    'access_token': access_token
                }
                response = await client.post(url, data=data)
            
            response.raise_for_status()
            result = response.json()
            return result.get("attachment_id")
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

async def send_meta_message(
        psid, 
        message, 
        message_object=MESSAGE_OBJECT_TYPE["facebook_page"]
):
    url = f"{FACEBOOK_URL['message']}?access_token={PAGE_ACCESS_TOKEN}"
    if (message_object == MESSAGE_OBJECT_TYPE["instagram"]):
        url = f"{INSTA_URL['message']}?access_token={INSTA_ACCESS_TOKEN}"

    if len(message) > 2000:
          message = message[:2000]

    payload = {
        "recipient": {"id": psid},
        "message": {"text": message}
    }
    headers = {'Content-Type': 'application/json'}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=headers)
    except Exception as e:
        print("Error sending message to FB:", e)

async def send_meta_image(psid: str,
                    image_source: str,
                    source_type: str = IMAGE_ATTACHMENT_TYPE["url"],
                    object_type=MESSAGE_OBJECT_TYPE["facebook_page"]):
    """
    Send an image (by public URL or local file) to psid.
    * source_type = "url"  : image_source is a publicly reachable https URL.
    * source_type = "file" : image_source is a path on disk; we first upload then send.
    """
    access_token = PAGE_ACCESS_TOKEN if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else INSTA_ACCESS_TOKEN
    url = f"{FACEBOOK_URL['message']}?access_token={access_token}" \
        if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] \
        else f"{INSTA_URL['message']}?access_token={access_token}"


    attachment_id = await _upload_image_get_attachment_id(image_source, source_type, object_type)
    print("Attachment ID:", attachment_id)

    if attachment_id:
        payload = {
            "recipient": {"id": psid},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"attachment_id": attachment_id}
                }
            }
        }
    else:
        # send by URL directly
        payload = {
            "recipient": {"id": psid},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"url": image_source, "is_reusable": False}
                }
            }
        }

    headers = {'Content-Type': 'application/json'}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code != 200:
                print("❌ Image send failed:", r.text)
    except Exception as e:
        print("Exception sending image:", e)

async def send_typing_indicator(psid, platform=MESSAGE_OBJECT_TYPE["facebook_page"]):
    url = f"{FACEBOOK_URL['typing']}?access_token={PAGE_ACCESS_TOKEN}"
    if (platform == MESSAGE_OBJECT_TYPE["instagram"]):
        url = f"{INSTA_URL['typing']}?access_token={INSTA_ACCESS_TOKEN}"
    
    payload = {
        "recipient": {"id": psid},
        "sender_action": "typing_on"
    }
    headers = {'Content-Type': 'application/json'}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

async def associate_label_to_conversation(label_id: str,
                                    conversation_id: str,
                                    object_type=MESSAGE_OBJECT_TYPE["facebook_page"]) -> bool:
    """
    Attach a custom label to a thread (conversation_id).
    Returns True on success, False otherwise.
    """
    access_token = os.getenv("PAGE_ACCESS_TOKEN") \
        if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] \
        else os.getenv("INSTA_ACCESS_TOKEN")
    base = FACEBOOK_URL['base'] if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else INSTA_URL['base']
    url = f"{base}/{conversation_id}/custom_labels"
    params = {"access_token": access_token}
    json_data = {"label": label_id}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, params=params, json=json_data)
        if resp.status_code != 200:
            print("Error associating label:", resp.status_code, resp.text)
        return resp.status_code == 200

async def get_labels_of_conversation(conversation_id: str,
                               object_type=MESSAGE_OBJECT_TYPE["facebook_page"]) -> list[str]:
    """
    Return list of label IDs attached to a thread.
    """
    access_token = os.getenv("PAGE_ACCESS_TOKEN") \
        if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] \
        else os.getenv("INSTA_ACCESS_TOKEN")
    base = FACEBOOK_URL['base'] if object_type == MESSAGE_OBJECT_TYPE["facebook_page"] else INSTA_URL['base']
    url = f"{base}/{conversation_id}/custom_labels"
    params = {"access_token": access_token}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return [item.get("id") for item in data]
        else:
            print("Error fetching conversation labels:", resp.status_code, resp.text)
            return []