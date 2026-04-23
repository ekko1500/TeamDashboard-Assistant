import requests
from datetime import datetime
import os

# Assumes environment variables are set
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_LIST_ID = os.getenv("TRELLO_LIST_ID")

def add_task_to_trello(task_text: str):
    """Your existing logic, now a reusable function."""
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_TOKEN,
        "idList": TRELLO_LIST_ID,
        "name": task_text[:512],
        "desc": f"Added via Telegram bot on {datetime.now()}",
        "pos": "top"
    }
    response = requests.post("https://api.trello.com/1/cards", params=params)
    response.raise_for_status() # Good practice to catch errors here
    return response.json()