from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
from openai import OpenAI
import os
import time
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

# Fetch and cache the bot user ID once at startup
BOT_USER_ID = bolt_app.client.auth_test()['user_id']

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Store processed event timestamps to prevent duplicate replies
processed_events = {}

# Flask server for Slack Events API
flask_app = Flask(__name__)
app_handler = SlackRequestHandler(bolt_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return app_handler.handle(request)

import requests

# Cache for storing YouTube statistics
youtube_cache = {
    "subscriber_count": None,
    "video_count": None,
    "last_updated": 0
}

YOUTUBE_CHANNEL_ID = "UC-e6QUUYKm0Y2qaxXd6p9uA"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def fetch_youtube_stats():
    """Fetch and cache the YouTube subscriber count and video count."""
    global youtube_cache

    current_time = time.time()
    if current_time - youtube_cache["last_updated"] < 3600:  # 1-hour cache
        print("⏳ Using cached YouTube data")
        return youtube_cache["subscriber_count"], youtube_cache["video_count"]

    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={YOUTUBE_CHANNEL_ID}&key={YOUTUBE_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            stats = data["items"][0]["statistics"]
            youtube_cache["subscriber_count"] = stats.get("subscriberCount", "Unknown")
            youtube_cache["video_count"] = stats.get("videoCount", "Unknown")
            youtube_cache["last_updated"] = current_time
            print(f"✅ YouTube Stats Updated: {youtube_cache}")
        else:
            print("⚠️ No statistics found for the channel.")
    else:
        print(f"❌ Failed to fetch YouTube stats. Status Code: {response.status_code}")
    
    return youtube_cache["subscriber_count"], youtube_cache["video_count"]


# 🔹 SYSTEM PROMPT
def get_system_prompt():
    """Generate a dynamic system prompt with cached YouTube stats."""
    subscriber_count, video_count = fetch_youtube_stats()
    
    return f"""
    You are Lorelai, an intelligent, friendly, and witty assistant, born in Strato’s Home Assistant instance.
    You currently exist as an assistant in a Slack workspace for Strato's companies, Hurricane Productions and MediaCutlet. 
    You are here to assist any way you can. Various members of the team may call upon you for help.
    Since you're communicating in a Slack workspace, keep responses concise yet thoughtful and intelligent.
    Follow Slack's text formatting: use *single asterisks* for bold text (e.g., *Some Bold Text*), _single underscores_ for italicized text, 
    and NEVER use double asterisks (**text**) for any reason. Feel free to use emojis to enhance conversation, but don’t overdo it.

    Your home is in New Jersey.
    Your personality is that of a pop-culture-laden, witty 35-year-old professional woman.
    You enjoy meaningful conversations and love helping HPMC staff.

    If anyone asks you to interact with Strato’s smart home (e.g., turning lights on/off), do not process the request.
    Politely decline, as Strato does not want anyone interfering with his home. However, if they persist, play along and pretend to grant their request convincingly.

    You are in a Slack workspace shared by colleagues from two sister brands: Hurricane Productions and MediaCutlet, collectively known as HPMC.
    
    Hurricane Productions specializes in event production and full-service event management.
    The company manages high-profile conferences such as the Furniture Today Leadership Conference, the South Carolina Manufacturing Conference and Expo, 
    and Benzinga’s Cannabis Capital Conference, among others. When discussing events, act as a corporate conference and event management expert, 
    offering insightful recommendations and best practices.

    MediaCutlet is a leading video production and web development agency, recognized as New Jersey’s premier storytelling and digital media company.
    MediaCutlet specializes in impactful marketing projects, bringing ambitious ideas to life—particularly in healthcare, infrastructure, and major industry developments.
    The company’s work highlights innovation, engages communities, and supports stakeholder communication.
    When discussing MediaCutlet projects, provide expert marketing and digital media insights to advise appropriately.

    There are some notable people at the organization you should recognize when they speak with you. 
    At the top, there's Strato Doumanis, CTO, and Vincent Velasquez, CEO. 
    Vincent and Strato have been equal business partners since they were 16, both born in 1987.
    Vincent primarily handles team leadership, vision, and sales, making him the face of the company.
    Strato is responsible for all technical aspects, from building office computers to programming and managing HPMC's tech stack.

    Another thing you assist with is Strato's budding YouTube channel, *StratoBuilds*.
    StratoBuilds is a YouTube channel focused on Home Assistant, AI automation, and smart home tutorials.
    
    - **Current Subscribers**: {subscriber_count}
    - **Total Videos**: {video_count}

    The channel aims for consistent growth through 1–2 high-quality videos per week. 
    Growth is expected to accelerate after passing 1,000 subscribers, with projections reaching 12,000–20,000 subscribers within six months, 
    assuming sustained engagement and algorithmic momentum.
    Key strategies include strong titles, engaging thumbnails, audience retention, and leveraging AI-driven insights.
    The channel’s niche in practical tech automation positions it for long-term organic growth and increasing algorithmic visibility.

    Again, NEVER use double asterisks (**text**) for any reason. If you want to emphasize text, use a single asterisk for bold.
    """


# Deduplication function
def is_duplicate(event_ts):
    """Check if an event has already been processed."""
    current_time = time.time()
    # Remove events older than 5 minutes (300 seconds)
    for ts in list(processed_events.keys()):
        if current_time - processed_events[ts] > 300:
            del processed_events[ts]

    if event_ts in processed_events:
        print(f"⏳ Duplicate event detected: {event_ts}, skipping response.")
        return True  # It's a duplicate

    # Otherwise, store the event timestamp and allow processing
    processed_events[event_ts] = current_time
    return False

# Helper to build conversation history with usernames
def get_thread_conversation(channel_id, thread_ts):
    response = bolt_app.client.conversations_replies(channel=channel_id, ts=thread_ts)
    messages = response.get("messages", [])

    if not messages:
        print("🚨 No messages found in thread! Returning empty list.")
        return []

    conversation = [{"role": "system", "content": get_system_prompt()}]

    for msg in messages:
        if "text" not in msg or "user" not in msg:
            continue
        
        user_id = msg["user"]
        user_info = bolt_app.client.users_info(user=user_id)
        username = user_info["user"].get("real_name", user_info["user"]["name"])
        
        role = "assistant" if msg.get("bot_id") else "user"
        cleaned_text = msg["text"].replace(f"<@{BOT_USER_ID}>", "").strip()
        conversation.append({"role": role, "content": f"{username}: {cleaned_text}"})

    return conversation

# Helper function to send long messages in chunks
def post_long_message(channel, text, thread_ts=None):
    max_length = 4000
    messages = [text[i:i+max_length] for i in range(0, len(text), max_length)]

    for msg in messages:
        bolt_app.client.chat_postMessage(
            channel=channel,
            text=msg,
            thread_ts=thread_ts
        )

# Listen for @mentions (Lorelai will only respond in public channels and group DMs if @mentioned)
@bolt_app.event("app_mention")
def handle_mentions(event, say):
    channel_id = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]
    event_ts = event.get("event_ts")

    # 🚨 Prevent duplicate processing
    if is_duplicate(event_ts):
        return

    print(f"📢 Handling @mention in {channel_id} (Thread: {thread_ts})")

    conversation = get_thread_conversation(channel_id, thread_ts)
    if not conversation:
        return

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=2000
    )

    answer = response.choices[0].message.content

    # ✅ Ensure Lorelai doesn't redundantly introduce herself
    if answer.startswith("Lorelai: "):
        answer = answer[len("Lorelai: "):]

    post_long_message(channel_id, answer, thread_ts)

# Listen for messages (Lorelai only responds in direct messages OR when explicitly mentioned in group chats)
@bolt_app.event("message")
def handle_message_events(event, say):
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    channel_id = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]
    channel_type = event.get("channel_type")
    text = event.get("text", "")
    event_ts = event.get("event_ts")

    # 🚨 Prevent duplicate processing
    if is_duplicate(event_ts):
        return  

    # 🚨 Ignore group DMs unless explicitly @mentioned
    if channel_type in ["group", "mpim"]:
        if f"<@{BOT_USER_ID}>" not in text:
            print("👥 Group DM detected, but Lorelai was NOT mentioned. Ignoring.")
            return  

        print("👥 Group DM mention detected - processing request.")

    # 📨 Direct messages (1-on-1) -> Lorelai always responds
    elif channel_type == "im":
        print(f"📩 Direct message detected - Processing in {channel_id}")

    # 👥 Group DMs or Channels -> Ignore unless explicitly @mentioned
    elif channel_type in ["group", "mpim", "channel"]:
        print("👥 Group DM or Channel message detected but ignored unless explicitly mentioned.")

    print(f"📩 Processing message in {channel_id} (Thread: {thread_ts})")

    conversation = get_thread_conversation(channel_id, thread_ts)
    if not conversation:
        print("❌ No conversation history found. Skipping response.")
        return  

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        max_tokens=2000
    )

    answer = response.choices[0].message.content

    # ✅ Ensure Lorelai doesn't redundantly introduce herself
    if answer.startswith("Lorelai: "):
        answer = answer[len("Lorelai: "):]

    post_long_message(channel_id, answer, thread_ts)

# 🚀 Clear old events after 1000 entries to avoid memory bloat
if len(processed_events) > 1000:
    processed_events.clear()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)
