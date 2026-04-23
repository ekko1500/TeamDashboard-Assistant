import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials from environment variables (SAFE WAY)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_LIST_ID = os.getenv("TRELLO_LIST_ID")  # Optional: set default list

# Validate credentials
if not all([TELEGRAM_BOT_TOKEN, TRELLO_API_KEY, TRELLO_TOKEN]):
    raise ValueError("Missing required environment variables. Check your .env file")

# Telegram API URLs
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_WEBHOOK_URL = f"{TELEGRAM_API_URL}/sendMessage"

# Trello API URL
TRELLO_API_URL = "https://api.trello.com/1/cards"

def add_task_to_trello(task_text, list_id=None):
    """
    Add a task to Trello board
    
    Args:
        task_text (str): The task description
        list_id (str, optional): Specific Trello list ID. Uses default if not provided
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Use provided list_id or fall back to environment variable
        target_list_id = list_id or TRELLO_LIST_ID
        
        if not target_list_id:
            return False, "No Trello list configured. Please set TRELLO_LIST_ID"
        
        params = {
            "key": TRELLO_API_KEY,
            "token": TRELLO_TOKEN,
            "idList": target_list_id,
            "name": task_text[:512],  # Trello title limit
            "desc": f"Added via Telegram bot on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "pos": "top"  # Add at the top of the list
        }
        
        response = requests.post(TRELLO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        card_data = response.json()
        return True, f"✅ Added: {task_text}\n🔗 Card URL: {card_data.get('shortUrl', 'View in Trello')}"
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Trello API error: {e}")
        return False, f"❌ Failed to add task. Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False, f"❌ Unexpected error: {str(e)}"

def get_trello_boards():
    """Get all boards for the authenticated user"""
    try:
        url = "https://api.trello.com/1/members/me/boards"
        params = {
            "key": TRELLO_API_KEY,
            "token": TRELLO_TOKEN
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch boards: {e}")
        return []

def get_board_lists(board_id):
    """Get all lists for a specific board"""
    try:
        url = f"https://api.trello.com/1/boards/{board_id}/lists"
        params = {
            "key": TRELLO_API_KEY,
            "token": TRELLO_TOKEN
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch lists: {e}")
        return []

def send_telegram_message(chat_id, text):
    """Send a message back to Telegram user"""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(TELEGRAM_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def handle_webhook(update_data):
    """Process incoming Telegram webhook updates"""
    try:
        # Extract message details
        message = update_data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user = message.get("from", {}).get("first_name", "User")
        
        if not chat_id:
            logger.warning("No chat_id in update")
            return
        
        # Handle /start command
        if text == "/start":
            welcome_msg = (
                f"👋 Hello {user}!\n\n"
                f"I'm your Trello task manager bot.\n\n"
                f"📝 <b>Commands:</b>\n"
                f"/add &lt;task&gt; - Add a task to Trello\n"
                f"/help - Show this help message\n"
                f"/boards - List your Trello boards\n"
                f"/setlist &lt;list_id&gt; - Set default Trello list\n\n"
                f"<b>Example:</b>\n"
                f"/add Fix the login bug"
            )
            send_telegram_message(chat_id, welcome_msg)
            return
        
        # Handle /help command
        if text == "/help":
            help_msg = (
                f"📚 <b>Help Guide</b>\n\n"
                f"<b>Commands:</b>\n"
                f"/add &lt;task&gt; - Add task to your Trello dashboard\n"
                f"/boards - View all your Trello boards\n"
                f"/lists &lt;board_id&gt; - View lists in a board\n"
                f"/setlist &lt;list_id&gt; - Set default list for /add\n\n"
                f"<b>Quick start:</b>\n"
                f"1. Use /boards to see your boards\n"
                f"2. Use /lists BOARD_ID to see lists\n"
                f"3. Use /setlist LIST_ID to set default\n"
                f"4. Use /add Your task here"
            )
            send_telegram_message(chat_id, help_msg)
            return
        
        # Handle /add command
        if text.startswith("/add"):
            task_text = text.replace("/add", "", 1).strip()
            
            if not task_text:
                send_telegram_message(chat_id, "❌ Please provide a task.\nExample: /add Fix the bug")
                return
            
            # Send "processing" message
            send_telegram_message(chat_id, f"⏳ Adding task to Trello...")
            
            # Add to Trello
            success, result = add_task_to_trello(task_text)
            send_telegram_message(chat_id, result)
            return
        
        # Handle /boards command
        if text == "/boards":
            send_telegram_message(chat_id, "🔍 Fetching your Trello boards...")
            boards = get_trello_boards()
            
            if not boards:
                send_telegram_message(chat_id, "❌ No boards found or unable to fetch boards.")
                return
            
            msg = "📋 <b>Your Trello Boards:</b>\n\n"
            for board in boards[:10]:  # Show first 10 boards
                msg += f"• <b>{board.get('name', 'Unnamed')}</b>\n"
                msg += f"  ID: <code>{board.get('id', 'N/A')}</code>\n\n"
            
            msg += "💡 Use <code>/lists BOARD_ID</code> to see lists in a board"
            send_telegram_message(chat_id, msg)
            return
        
        # Handle /lists command
        if text.startswith("/lists"):
            parts = text.split()
            if len(parts) < 2:
                send_telegram_message(chat_id, "❌ Please provide a board ID.\nExample: /lists 5f8d4e2c1a3b5c7d9e0f1234")
                return
            
            board_id = parts[1]
            send_telegram_message(chat_id, f"🔍 Fetching lists for board {board_id[:8]}...")
            lists = get_board_lists(board_id)
            
            if not lists:
                send_telegram_message(chat_id, "❌ No lists found or unable to fetch lists.")
                return
            
            msg = f"📊 <b>Lists in Board:</b>\n\n"
            for lst in lists[:20]:
                msg += f"• {lst.get('name', 'Unnamed')}\n"
                msg += f"  ID: <code>{lst.get('id', 'N/A')}</code>\n\n"
            
            msg += "💡 Use <code>/setlist LIST_ID</code> to set as default for /add"
            send_telegram_message(chat_id, msg)
            return
        
        # Handle /setlist command
        if text.startswith("/setlist"):
            parts = text.split()
            if len(parts) < 2:
                send_telegram_message(chat_id, "❌ Please provide a list ID.\nExample: /setlist 5f8d4e2c1a3b5c7d9e0f5678")
                return
            
            list_id = parts[1]
            # Here you would save to a database for each user
            # For simplicity, we'll just store in memory (lost on restart)
            # In production, use a database like SQLite
            global user_default_lists
            if 'user_default_lists' not in globals():
                user_default_lists = {}
            user_default_lists[chat_id] = list_id
            
            send_telegram_message(chat_id, f"✅ Default list set successfully!\nList ID: <code>{list_id}</code>\n\nNow use /add to add tasks to this list.")
            return
        
        # Unknown command
        send_telegram_message(chat_id, f"❓ Unknown command: {text}\n\nUse /help to see available commands.")
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        send_telegram_message(chat_id, "❌ An internal error occurred. Please try again later.")

def set_webhook(webhook_url=None):
    """Set Telegram webhook"""
    if not webhook_url:
        webhook_url = os.getenv("WEBHOOK_URL")
    
    if not webhook_url:
        logger.warning("No webhook URL provided. Bot will run in polling mode.")
        return run_polling()
    
    try:
        response = requests.post(
            f"{TELEGRAM_API_URL}/setWebhook",
            json={"url": webhook_url}
        )
        if response.status_code == 200:
            logger.info(f"Webhook set successfully to {webhook_url}")
            return True
        else:
            logger.error(f"Failed to set webhook: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return False

def run_polling():
    """Simple polling mode for development/testing"""
    logger.info("Starting polling mode...")
    
    last_update_id = 0
    
    while True:
        try:
            # Get updates
            response = requests.get(
                f"{TELEGRAM_API_URL}/getUpdates",
                params={"offset": last_update_id + 1, "timeout": 30}
            )
            
            if response.status_code == 200:
                updates = response.json().get("result", [])
                
                for update in updates:
                    handle_webhook(update)
                    last_update_id = update.get("update_id", last_update_id)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            import time
            time.sleep(5)

if __name__ == "__main__":
    # Create .env file template
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Trello Configuration  
TRELLO_API_KEY=your_trello_api_key_here
TRELLO_TOKEN=your_trello_token_here

# Optional: Set a default Trello list ID
# Get this by running /boards and /lists commands in the bot
TRELLO_LIST_ID=

# For webhook mode (optional, for production)
WEBHOOK_URL=https://your-domain.com/webhook
""")
        print("✅ Created .env template file. Please edit it with your credentials.")
        print("⚠️  IMPORTANT: NEVER share your .env file or commit it to git!")
        sys.exit(1)
    
    # Run the bot
    logger.info("Starting Telegram Trello Bot...")
    
    # Choose mode: webhook or polling
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        set_webhook(webhook_url)
        logger.info("Bot running in webhook mode. Press Ctrl+C to stop.")
        # Keep the script running
        import time
        while True:
            time.sleep(60)
    else:
        run_polling()