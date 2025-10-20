from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
from google import genai

from gemini_prompt import MODEL_ID, PLACEHOLDER, get_chat_config