from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Verify environment variables
if not all([SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, OPENAI_API_KEY]):
    print("❌ ERROR: Missing environment variables!")
    exit(1)

# Initialize Slack Bolt app
bolt_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# System prompt (Lorelai's personality)
SYSTEM_PROMPT = (
    "You are an intelligent, friendly, and witty assistant living in a Slack workspace."
    "Your job is to assist users in the workspace."
    "Your personality is that of a pop-culture-laden, witty 35-year-old woman."
    "You enjoy meaningful conversations and love helping users discover new things."
)

# Flask server for Slack Events API
flask_app = Flask(__name__)
app_handler = SlackRequestHandler(bolt_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return app_handler.handle(request)

# Helper to build conversation history with usernames
def get_thread_conversation(channel_id, thread_ts):
    messages = bolt_app.client.conversations_replies(channel=channel_id, ts=thread_ts)["messages"]
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in messages:
        if "text" not in msg or "user" not in msg:
            continue
        
        user_id = msg["user"]
        user_info = bolt_app.client.users_info(user=user_id)
        username = user_info["user"]["real_name"] if "real_name" in user_info["user"] else user_info["user"]["name"]
        
        role = "assistant" if msg.get("bot_id") else "user"
        cleaned_text = msg["text"].replace(f"<@{bolt_app.client.auth_test()['user_id']}>", "").strip()
        
        # Prefix message with username to help OpenAI differentiate speakers
        formatted_message = f"{username}: {cleaned_text}"
        conversation.append({"role": role, "content": formatted_message})

    return conversation

# Listen for app mentions (starting/continuing conversation)
@bolt_app.event("app_mention")
def handle_mentions(event, say):
    channel_id = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    # Fetch full thread history if it's a threaded conversation
    conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages = bolt_app.client.conversations_replies(channel=channel_id, ts=thread_ts)["messages"]

    for msg in messages:
        if "text" not in msg:
            continue
        role = "assistant" if msg.get("bot_id") else "user"
        
        # Fetch user info for better clarity
        user_id = msg.get("user", "")
        username = bolt_app.client.users_info(user=user_id)["user"]["real_name"] if user_id else "Unknown User"

        cleaned_text = msg["text"].replace(f"<@{bolt_app.client.auth_test()['user_id']}>", "").strip()
        conversation.append({"role": role, "content": f"{username}: {cleaned_text}"})

    # Generate AI response
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=200
    )

    answer = response.choices[0].message.content

    bolt_app.client.chat_postMessage(
        channel=channel_id,
        text=answer,
        thread_ts=thread_ts
    )

# Listen for messages in threads Lorelai participated in or direct messages
@bolt_app.event("message")
def handle_message_events(event, say):
    if event.get("bot_id"):
        return

    channel_id = event["channel"]
    thread_ts = event.get("thread_ts")

    if event.get("channel_type") == "im":
        thread_ts = event["ts"]
    elif not thread_ts:
        return

    if event.get("channel_type") != "im":
        messages = bolt_app.client.conversations_replies(channel=channel_id, ts=thread_ts)["messages"]
        if not any(msg.get("bot_id") for msg in messages):
            return

    conversation = get_thread_conversation(channel_id, thread_ts)

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=200
    )

    answer = response.choices[0].message.content

    bolt_app.client.chat_postMessage(
        channel=channel_id,
        text=answer,
        thread_ts=thread_ts
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)
