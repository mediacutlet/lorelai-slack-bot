# Lorelai - AI-Powered Slack Assistant 🤖💬

Lorelai is an intelligent, friendly, and witty Chat GPT-powered Slack assistant designed to enhance interactions within your Slack workspace.
---

## 📌 Features

- ✅ AI-driven conversations within Slack
- ✅ Context-aware replies leveraging conversation history
- ✅ Expert guidance for event management, video production, and digital media
- ✅ Deployed using **Heroku** with streamlined CI/CD through Git
- ✅ Secure and efficient Slack API interactions using **Slack Bolt**

---

## 🚀 Prerequisites

Before setting up Lorelai, ensure you have:

- ✅ Access to a **Slack workspace**
- ✅ A **Heroku account**
- ✅ **Git and Heroku CLI** installed on your computer
- ✅ **Python 3.8 or newer** installed, with a virtual environment

---

## 🔧 Slack Setup

### 1️⃣ Create and Configure a Slack App

1. Go to the [Slack API Dashboard](https://api.slack.com/apps) and create a new app.
2. Choose **"From scratch"**, name it **Lorelai**, and select your Slack workspace.
3. Navigate to **OAuth & Permissions** and assign these bot scopes:

```
app_mentions:read
chat:write
channels:history
groups:history
im:history
mpim:history
users:read
reactions:read
```

4. Click **Install App to Workspace**, authorize it, and note down the **Bot User OAuth Token**.

### 2️⃣ Enable Event Subscriptions

1. Go to **Event Subscriptions** in your Slack app settings and enable it.
2. Set your **Request URL** to:

```
https://your-heroku-app.herokuapp.com/slack/events
```

3. Subscribe to these bot events:

```
app_mention
message.im
message.channels
message.groups
reaction_added
```

4. Click **Save** and then **Reinstall App**.

---

## 🛠️ Local Development Setup

Clone your repository and install dependencies:

```bash
git clone <your-repo-url>
cd lorelai
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in your root directory and add:

```dotenv
SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
OPENAI_API_KEY=your-openai-api-key
```

Start your local server:

```bash
python app.py
```

---

## 🚢 Deploy to Heroku

1. Log in and create your Heroku app:

```bash
heroku login
heroku create your-heroku-app-name
```

2. Set Heroku config variables:

```bash
heroku config:set SLACK_BOT_TOKEN=your-slack-bot-token
heroku config:set SLACK_SIGNING_SECRET=your-slack-signing-secret
heroku config:set OPENAI_API_KEY=your-openai-api-key
```

3. Deploy via Git:

```bash
git add .
git commit -m "Deploy Lorelai Slack assistant"
git push heroku main
```

4. Ensure your Heroku dynos are running:

```bash
heroku ps:scale web=1
```

---

## 📦 Dependencies

- Flask
- Slack Bolt
- Slack SDK
- OpenAI Python SDK
- python-dotenv
- gunicorn

Ensure your `requirements.txt` contains:

```text
flask
slack-bolt
slack-sdk
python-dotenv
openai
gunicorn
```

---

## 📝 License

MIT License © MediaCutlet 2025.

