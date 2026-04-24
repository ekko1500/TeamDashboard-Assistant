from fastapi import FastAPI, Request, Response
import logging
import requests
import asyncio
from config import TELEGRAM_API_URL, WEBHOOK_URL, PORT
from bot_handler import handle_webhook

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Trello Bot API")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Telegram Trello Bot is running"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint"""
    try:
        update_data = await request.json()
        # Handle update in a background task to respond quickly to Telegram
        # Telegram expects a 200 OK within a short timeout
        asyncio.create_task(async_handle_webhook(update_data))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error in webhook endpoint: {e}")
        return Response(status_code=200)  # Always return 200 to Telegram

async def async_handle_webhook(update_data):
    """Wrapper to handle webhook data asynchronously"""
    try:
        handle_webhook(update_data)
    except Exception as e:
        logger.error(f"Async webhook handler error: {e}")

def set_webhook():
    """Set Telegram webhook on startup if URL is provided"""
    if not WEBHOOK_URL:
        logger.warning("No WEBHOOK_URL provided. Bot will NOT receive updates via webhook.")
        return
    
    try:
        url = f"{TELEGRAM_API_URL}/setWebhook"
        payload = {"url": f"{WEBHOOK_URL}/webhook"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Webhook set successfully to {WEBHOOK_URL}/webhook")
        else:
            logger.error(f"Failed to set webhook: {response.text}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

def run_polling():
    """Simple polling mode for development"""
    logger.info("Starting polling mode...")
    last_update_id = 0
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get("result", [])
                for update in updates:
                    handle_webhook(update)
                    last_update_id = update.get("update_id", last_update_id)
            elif response.status_code == 409:
                logger.error("Conflict: Is another bot instance running or is a webhook set?")
                break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            asyncio.run(asyncio.sleep(5))

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    if WEBHOOK_URL:
        set_webhook()

if __name__ == "__main__":
    import uvicorn
    # If no webhook URL is set, we might want to run polling instead
    # However, for a FastAPI app, we usually run the server.
    # We can run polling in a separate thread/task if needed, but 
    # usually local testing is done via uvicorn and manual testing or 
    # by just setting WEBHOOK_URL to empty to skip webhook setup.
    
    if not WEBHOOK_URL:
        # For local dev without webhook, you might want to run polling
        # But uvicorn blocks. So we run polling in a separate process/thread
        # only if explicitly intended. For now, let's keep it simple.
        logger.info("Running in polling mode (local dev)...")
        run_polling()
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)