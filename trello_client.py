import requests
import logging
from datetime import datetime
from config import TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_LIST_ID, TRELLO_API_URL

logger = logging.getLogger(__name__)

def add_task_to_trello(task_text, list_id=None):
    """
    Add a task to Trello board
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
