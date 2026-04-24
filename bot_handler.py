import requests
import logging
import html
from config import TELEGRAM_SEND_MESSAGE_URL, TRELLO_LIST_ID
from trello_client import (
    add_task_to_trello, 
    get_trello_boards, 
    get_board_lists, 
    get_list_cards, 
    update_card
)

logger = logging.getLogger(__name__)

# Simple in-memory storage for user list IDs (Reset on restart)
# In production, use a database.
user_default_lists = {}
# Cache to map numbers (1, 2, 3...) to Trello Card data
# chat_id -> [{"id": "...", "name": "..."}, ...]
user_task_cache = {} 

def send_telegram_message(chat_id, text, parse_mode="HTML"):
    """Send a message back to Telegram user"""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        response = requests.post(TELEGRAM_SEND_MESSAGE_URL, json=payload, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            # Fallback if HTML parsing failed
            if "can't parse entities" in response.text.lower():
                logger.info("Retrying without HTML parse mode...")
                payload["parse_mode"] = None
                response = requests.post(TELEGRAM_SEND_MESSAGE_URL, json=payload, timeout=10)
        
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def handle_webhook(update_data):
    """Process incoming Telegram webhook updates"""
    try:
        logger.info(f"Handling update: {update_data}")
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
                f"/add &lt;task&gt; - Add a task\n"
                f"/tasks - List your pending tasks\n"
                f"/done &lt;number&gt; - Mark a task as checked\n"
                f"/help - Show all commands\n"
                f"/boards - List your Trello boards\n\n"
                f"<b>Example:</b>\n"
                f"/add Buy some groceries"
            )
            send_telegram_message(chat_id, welcome_msg)
            return
        
        # Handle /help command
        if text == "/help":
            help_msg = (
                f"📚 <b>Help Guide</b>\n\n"
                f"<b>Core Commands:</b>\n"
                f"/add &lt;task&gt; - Add task to your Trello list\n"
                f"/tasks - View all pending tasks (numbered)\n"
                f"/done &lt;number&gt; - Mark a task as checked by its number\n\n"
                f"<b>Setup Commands:</b>\n"
                f"/boards - View all your Trello boards\n"
                f"/lists &lt;board_id&gt; - View lists in a board\n"
                f"/setlist &lt;list_id&gt; - Set default list for tasks\n\n"
                f"<b>Example Flow:</b>\n"
                f"1. `/tasks` -> Lists tasks with (1), (2)...\n"
                f"2. `/done 1` -> Marks task #1 as checked ✅"
            )
            send_telegram_message(chat_id, help_msg)
            return
        
        # Handle /tasks command
        if text == "/tasks":
            # Use user's preference or system default
            target_list_id = user_default_lists.get(chat_id) or TRELLO_LIST_ID
            
            if not target_list_id:
                send_telegram_message(chat_id, "❌ No default list configured. Use /setlist to set one.")
                return
                
            send_telegram_message(chat_id, "🔍 Fetching your tasks...")
            cards = get_list_cards(target_list_id)
            
            if cards is None:
                send_telegram_message(chat_id, "❌ Error fetching tasks from Trello. Please check your credentials.")
                return
            
            if not cards:
                send_telegram_message(chat_id, "✨ You have no pending tasks!")
                return
            
            # Update cache with full card objects
            user_task_cache[chat_id] = cards
            
            msg = "📋 <b>Your Pending Tasks:</b>\n\n"
            for i, card in enumerate(cards, 1):
                name = card.get('name', 'Unnamed task')
                safe_name = html.escape(name)
                msg += f"{i}. <b>{safe_name}</b>\n"
            
            msg += "\n💡 Use `/done <number>` to mark a task as checked."
            send_telegram_message(chat_id, msg)
            return
            
        # Handle /done command
        if text.startswith("/done"):
            parts = text.split()
            if len(parts) < 2:
                send_telegram_message(chat_id, "❌ Please provide a task number.\nExample: /done 1")
                return
                
            try:
                index = int(parts[1]) - 1
                cached_cards = user_task_cache.get(chat_id, [])
                
                if 0 <= index < len(cached_cards):
                    card = cached_cards[index]
                    card_id = card.get('id')
                    current_name = card.get('name', '')
                    
                    if current_name.startswith("✅"):
                        send_telegram_message(chat_id, "💡 This task is already checked!")
                        return
                        
                    send_telegram_message(chat_id, f"⏳ Marking task '{html.escape(current_name)}' as checked...")
                    
                    new_name = f"✅ {current_name}"
                    if update_card(card_id, name=new_name, due_complete=True):
                        # Update local cache name so it doesn't need to re-fetch to see the check
                        card['name'] = new_name
                        send_telegram_message(chat_id, f"✅ Task marked as checked!")
                    else:
                        send_telegram_message(chat_id, "❌ Failed to update task in Trello.")
                else:
                    send_telegram_message(chat_id, "❌ Invalid task number. Use /tasks to see current numbers.")
            except ValueError:
                send_telegram_message(chat_id, "❌ Invalid number format. Use /done 1")
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
