# utils/debounce.py
import threading
import time
from typing import Dict, List, Callable, TypedDict

class Message(TypedDict):
    text: str
    reply_to: str | None

class DebounceMessageController:
    """
    Per-user debounce: collect messages during a quiet-period window
    and call a callback once after inactivity.
    """
    def __init__(self, wait_seconds: int = 10):
        self.wait_seconds = wait_seconds
        self.buffers: Dict[str, List[Message]] = {}
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()

    def add_message(
        self,
        user_id: str,
        message: Message,
        callback: Callable[[str, List[str]], None], 
    ):
        print(f"[DebounceMessageController] add_message called, user_id = {user_id}, message = {message}")
        """Add a message and (re)start that user’s debounce timer."""
        with self.lock:
            # append to buffer
            self.buffers.setdefault(user_id, []).append(message)

            # cancel previous timer if running
            if user_id in self.timers:
                self.timers[user_id].cancel()

            # start fresh timer
            timer = threading.Timer(
                self.wait_seconds,
                self._fire,
                args=(user_id, callback)
            )
            timer.daemon = True
            self.timers[user_id] = timer
            timer.start()

    def _fire(self, user_id: str, callback: Callable[[str, List[str]], None]):
        print(f"[DebounceMessageController] _fire called, user_id = {user_id}")
        """Timer expiry → call callback with all buffered messages."""
        with self.lock:
            messages = self.buffers.pop(user_id, [])
            self.timers.pop(user_id, None)
        if messages:
            callback(user_id, messages)