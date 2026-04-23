from fastapi import FastAPI, Request, Response, HTTPException
from trello_service import add_task_to_trello
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Your single backend endpoint."""
    try:
        update = await request.json()
        logger.info(f"Received update: {update}")

        # 1. Extract the command and user info from 'update'
        # This replaces your old 'handle_webhook' function's parsing logic.
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if not chat_id:
            return Response(status_code=200) # Acknowledge receipt

        # 2. Handle the "/add" command
        if text and text.startswith("/add"):
            task = text.replace("/add", "", 1).strip()
            if task:
                # 3. Call your existing Trello service
                card = add_task_to_trello(task)
                # 4. Send a reply back to the user via Telegram API
                await send_telegram_message(chat_id, f"✅ Added: {task}\n{card.get('shortUrl')}")
            else:
                await send_telegram_message(chat_id, "Usage: /add Your task here")

        # ... handle /start, /help, etc. in the same way ...

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        # It's crucial to return 200 OK to Telegram, even on error.
        # Otherwise, Telegram will keep retrying the failed update.
        return Response(status_code=200)

async def send_telegram_message(chat_id: int, text: str):
    """Helper function to send messages back to the user."""
    import requests
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)