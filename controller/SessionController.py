from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, TypedDict

from google import genai
from google.genai.chats import Chat

from gemini_prompt import MODEL_ID, get_chat_config

SESSION_CAPACITY = 100
SESSION_TIME_THRESHOLD = 86400  # in second
SUSPENSION_TIME_THRESHOLD = 30  # in second / change to 86400 for production

class SuspenInfo(TypedDict):
    suspended_time: datetime | None
class ChatEntryDict(TypedDict):
    chat: Any | Chat
    last_date: datetime
    suspended_info: SuspenInfo | None


class SessionController:
    def __init__(
        self,
        client: genai.Client | Any,
        session_capacity: int = SESSION_CAPACITY,
        session_time_threshold: int = SESSION_TIME_THRESHOLD,
    ):
        """
        Initializes a new SessionController instance.
        """
        self.sessions: OrderedDict[type, ChatEntryDict] = OrderedDict()
        self.client = client
        self.session_capacity = session_capacity
        self.session_time_threshold = session_time_threshold

    def _sort_chat_sessions_by_date(self):
        # print("[Session Controller] sort chat sessions by date")
        # sort newest to oldest
        self.sessions = OrderedDict(
            sorted(
                self.sessions.items(),
                key=lambda item: item[1]["last_date"],
                reverse=True,  # True: newest to oldest
            )
        )

    def _sort_and_clean_chat_sessions(self, current_time: datetime | None = None):
        # print("[Session Controller] ssort_and_clean_chat_sessions")
        current_time = current_time if current_time else datetime.now()

        self._sort_chat_sessions_by_date()

        # delete by capacity
        if len(self.sessions) > self.session_capacity:
            n_session = len(self.sessions) - self.session_capacity
            for _ in range(n_session):
                self.sessions.popitem(last=True)

        # delete by time
        # print("[Session Controller] get delete", self.sessions)
        id_to_delete = set()
        for sender_id in reversed(self.sessions):
            chat_session_date = self.sessions[sender_id]["last_date"]
            if current_time - chat_session_date >= timedelta(
                seconds=self.session_time_threshold
            ):
                id_to_delete.add(sender_id)
            else:
                # dict is ordered and sorted, break when there is no more session
                # past the time threshold.
                break
        
        # print("[Session Controller] delete chat sessions by time", id_to_delete)
        for sender_id in id_to_delete:
            self.delete_session(sender_id)

        # print("[Session Controller] wtf")

    def create_session(self, user_id):
        self.sessions[user_id] = {
            "chat": self.client.chats.create(
                model=MODEL_ID,
                config=get_chat_config(),
            ),
            "last_date": datetime.now(),
            "suspended_info": None,
        }
        return self.sessions[user_id]

    def get_session(self, user_id):
        """
        Retrieves the session for a user.
        :param user_id: The ID of the user.
        :return: The session data or None if no session exists.
        """
        # print("[Session Controller] get session for user:", user_id)
        if user_id not in self.sessions:
            session = self.create_session(user_id)
        else:
            session = self.sessions.get(user_id)

        # print("[Session Controller] session", session)

        # update chat session time to now
        current_time = datetime.now()
        session["last_date"] = current_time

        # delete chat session if past certain threshold, user who triggers this is
        # one lucky bastard.
        self._sort_and_clean_chat_sessions(current_time)

        # check if the session is suspended
        print("[Sesssion Controller] check suspension", session["suspended_info"])
        if (session["suspended_info"] is not None):
            # still suspended
            if (session["suspended_info"]["suspended_time"] > datetime.now()):
                return None
            else:
                # unsuspend
                session["suspended_info"] = None

        return session

    def delete_session(self, user_id):
        """
        Deletes the session for a user.
        :param user_id: The ID of the user.
        :return: None
        """
        if user_id in self.sessions:
            self.sessions.pop(user_id)

    def suspend_session(self, user_id):
        """
        Suspends the session for a user.
        :param user_id: The ID of the user.
        :return: None
        """
        if user_id in self.sessions:
            print("[Sesssion Controller] Suspending session for user:", user_id)
            self.sessions[user_id]["suspended_info"] = {
                "suspended_time": datetime.now() + timedelta(seconds=SUSPENSION_TIME_THRESHOLD)
            }
