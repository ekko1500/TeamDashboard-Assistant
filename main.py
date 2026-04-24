import logging

# Configure logging IMMEDIATELY before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import asyncio
import requests
from fastapi import FastAPI, Request, Response
from config import TELEGRAM_API_URL, WEBHOOK_URL, PORT
from bot_handler import handle_webhook

app = FastAPI(title="Telegram Trello Bot API")

@app.get("/")
async def root():
    """Health check endpoint"""
    logger.info("Health check endpoint called")
    return {"status": "ok", "message": "Telegram Trello Bot is running"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint"""
    try:
        update_data = await request.json()
        logger.info(f"Incoming webhook update: {update_data}")
        # Always handle asynchronously to keep the endpoint fast
        asyncio.create_task(async_handle_webhook(update_data))
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error in webhook endpoint: {e}")
        return Response(status_code=200)

async def async_handle_webhook(update_data):
    """Wrapper to handle webhook data asynchronously"""
    try:
        handle_webhook(update_data)
    except Exception as e:
        logger.error(f"Async webhook handler error: {e}")

def set_webhook():
    """Set Telegram webhook on startup"""
    if not WEBHOOK_URL:
        return
    
    try:
        url = f"{TELEGRAM_API_URL}/setWebhook"
        payload = {"url": f"{WEBHOOK_URL}/webhook"}
        logger.info(f"Setting webhook to {WEBHOOK_URL}/webhook...")
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Webhook set successfully")
        else:
            logger.error(f"Failed to set webhook: {response.text}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

async def run_polling_async():
    """Asynchronous polling mode for development"""
    logger.info("Starting asynchronous polling mode...")
    last_update_id = 0
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            
            # Using loop.run_in_executor for synchronous requests call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, params=params, timeout=25)
            )
            
            if response.status_code == 200:
                updates = response.json().get("result", [])
                for update in updates:
                    logger.info(f"Received polling update: {update}")
                    handle_webhook(update)
                    last_update_id = update.get("update_id", last_update_id)
            elif response.status_code == 409:
                logger.error("Conflict: A webhook is already set or another bot is polling.")
                break
            else:
                logger.warning(f"Polling error {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Polling exception: {e}")
            await asyncio.sleep(5)
        
        # Small delay to prevent tight loop in case of errors
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    if WEBHOOK_URL:
        set_webhook()
    else:
        logger.info("No WEBHOOK_URL set. Starting background polling task...")
        asyncio.create_task(run_polling_async())

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}...")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
