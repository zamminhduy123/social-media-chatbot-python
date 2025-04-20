# Facebook Chatbot using gemini & Facebook webhook (customize for KNI.vn)

This is an AI-powered chatbot built for [KNI Education](https://kni.vn), a leading center for TestAS preparation and German study consultation in Vietnam. The chatbot integrates Google Gemini (via `google-genai`) with Facebook Messenger to provide friendly and informative responses to prospective students.

---

## 🚀 Features

- ✨ AI-based replies powered by **Gemini Pro (Google GenAI)**
- 💬 Facebook Messenger integration using webhook
- 🇻🇳 Vietnamese prompt customization
- 🔒 Secure config management via `.env`
- 🌐 Deployable on **Render**, Railway, or VPS

---

## 🧱 Tech Stack

- `Flask` – lightweight web server
- `google-genai` – Gemini Pro access
- `python-dotenv` – environment variable management
- `Gunicorn` – WSGI server for production
- `Facebook Graph API` – for Messenger integration

---

## 🛠 Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/facebook-chatbot.git
   cd facebook-chatbot
2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
4. **Configure environment variables**
   ```bash
   GEMINI_API_KEY=your-gemini-api-key
    VERIFY_TOKEN=kni-verify-token
    PAGE_ACCESS_TOKEN=your-facebook-page-access-token

--- 

## ▶️ Local Development

Run Flask development server:
```bash
   python app.py
```
Or with Gunicorn (for testing production mode):

```bash
   gunicorn -w 4 -b 0.0.0.0:3000 app:app
```

## 🌐 Webhook Verification (Facebook Setup)
```bash
   GET /webhook?hub.verify_token=kni-verify-token&hub.challenge=123456&hub.mode=subscribe
```

## 🤝 About KNI Education

KNI Education is a TestAS prep center helping Vietnamese students prepare for academic studies in Germany.
	•	95% pass rate for TestAS
	•	Expert tutor: ABB Robotics Engineer, 125/130 TestAS scorer
	•	Free resources: Core Test + Module
	•	Personalized support until goal is achieved

Visit: https://kni.vn
