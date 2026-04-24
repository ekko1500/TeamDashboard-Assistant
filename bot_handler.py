import requests
import logging
from config import TELEGRAM_SEND_MESSAGE_URL
from trello_client import add_task_to_trello, get_trello_boards, get_board_lists

logger = logging.getLogger(__name__)

# Simple in-memory storage for user list IDs (Reset on restart)
# In production, use a database.
user_default_lists = {}

def send_telegram_message(chat_id, text):
    """Send a message back to Telegram user"""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(TELEGRAM_SEND_MESSAGE_URL, json=payload, timeout=10)
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
            
            # Use user's preference if set
            custom_list_id = user_default_lists.get(chat_id)
            
            # Add to Trello
            success, result = add_task_to_trello(task_text, list_id=custom_list_id)
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
            user_default_lists[chat_id] = list_id
            
            send_telegram_message(chat_id, f"✅ Default list set successfully!\nList ID: <code>{list_id}</code>\n\nNow use /add to add tasks to this list.")
            return
        
        # Unknown command (but only if it looks like a command starting with /)
        if text.startswith("/"):
            send_telegram_message(chat_id, f"❓ Unknown command: {text}\n\nUse /help to see available commands.")
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        send_telegram_message(chat_id, "❌ An internal error occurred. Please try again later.")
