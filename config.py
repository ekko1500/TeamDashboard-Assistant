import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing from environment variables")

# Trello Configuration
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_LIST_ID = os.getenv("TRELLO_LIST_ID")

if not all([TRELLO_API_KEY, TRELLO_TOKEN]):
    raise ValueError("Trello credentials (TRELLO_API_KEY, TRELLO_TOKEN) are missing")

# Telegram API URLs
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
# Correcting this: the webhook URL should be the endpoint, but for sending messages it should be /sendMessage
TELEGRAM_SEND_MESSAGE_URL = f"{TELEGRAM_API_URL}/sendMessage"

# Trello API URL
TRELLO_API_URL = "https://api.trello.com/1/cards"

# Webhook Configuration (Optional for polling)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))
