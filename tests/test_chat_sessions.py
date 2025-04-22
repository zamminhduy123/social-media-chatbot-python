import pytest
from collections import OrderedDict
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import time

from SessionController import SessionController  # replace with actual path

@pytest.fixture
def mock_client():
    mock_chat = MagicMock()
    mock_chat.send_message.return_value.text = "Mock response"

    mock_client = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    return mock_client

def test_create_and_get_session(mock_client):
    controller = SessionController(mock_client, session_capacity=5, session_time_threshold=60)
    user_id = "user1"

    session = controller.get_session(user_id)

    assert user_id in controller.sessions
    assert "chat" in session
    assert "last_date" in session

def test_session_reuse_updates_time(mock_client):
    controller = SessionController(mock_client)
    user_id = "user2"

    first_session = controller.get_session(user_id)
    first_time = first_session["last_date"]

    time.sleep(1)

    second_session = controller.get_session(user_id)
    second_time = second_session["last_date"]

    print(first_time)
    print(second_time)

    assert first_session is second_session
    assert second_time > first_time

def test_capacity_cleanup(mock_client):
    controller = SessionController(mock_client, session_capacity=3)
    now = datetime.now()

    for i in range(5):
        controller.sessions[f"user{i}"] = {
            "chat": MagicMock(),
            "last_date": now - timedelta(seconds=i * 10)
        }

    controller._sort_and_clean_chat_sessions(now)

    assert len(controller.sessions) == 3

def test_time_threshold_cleanup(mock_client):
    controller = SessionController(mock_client, session_capacity=10, session_time_threshold=30)
    now = datetime.now()

    controller.sessions["user1"] = {
        "chat": MagicMock(),
        "last_date": now - timedelta(seconds=10)
    }
    controller.sessions["user2"] = {
        "chat": MagicMock(),
        "last_date": now - timedelta(seconds=30)
    }
    controller.sessions["user3"] = {
        "chat": MagicMock(),
        "last_date": now - timedelta(seconds=60)
    }
    controller.sessions["user4"] = {
        "chat": MagicMock(),
        "last_date": now - timedelta(seconds=25)
    }
    controller.sessions["user5"] = {
        "chat": MagicMock(),
        "last_date": now - timedelta(seconds=120)
    }

    controller._sort_and_clean_chat_sessions(now)

    assert "user2" not in controller.sessions
    assert "user3" not in controller.sessions
    assert "user5" not in controller.sessions

    assert "user1" in controller.sessions
    assert "user4" in controller.sessions

def test_delete_session(mock_client):
    controller = SessionController(mock_client)
    user_id = "user3"
    controller.get_session(user_id)
    assert user_id in controller.sessions

    controller.delete_session(user_id)
    assert user_id not in controller.sessions
