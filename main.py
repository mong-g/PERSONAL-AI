import os
import asyncio
import logging
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from core.memory import MemoryManager
from core.intelligence import get_ai_response, detect_and_save_facts

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Simple Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Elijah is alive and running Version 2.5!")
    
    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.getenv("PORT", 8000))
    server_address = ('', port)
    try:
        httpd = HTTPServer(server_address, HealthCheckHandler)
        logging.info(f"Health check server starting on port {port}...")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health check server failed: {e}")

memory_manager = MemoryManager()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling an update:", exc_info=context.error)
    if "Timed out" in str(context.error):
        return
        
    if update and isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Elijah: I'm having a bit of a connection hiccup with Telegram. Give me a second!"
            )
        except Exception:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    authorized_user = os.getenv("TELEGRAM_USER_ID")
    
    if authorized_user and user_id != authorized_user:
        logging.warning(f"Unauthorized access attempt from user ID: {user_id}")
        return

    message_text = update.message.text or update.message.caption
    image = None
    tmp_path = None

    if update.message.photo:
        logging.info(f"Received photo from {user_id}")
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
                await photo_file.download_to_drive(tmp_path)
                image = Image.open(tmp_path)
        except Exception as e:
            logging.error(f"Error downloading photo: {e}")
            return
    else:
        logging.info(f"Received message from {user_id}: {message_text}")

    # 1. Check for onboarding (Lazy & Async)
    is_onboarding = False
    try:
        def check_onboarding():
            coll = memory_manager.get_collection()
            return coll.count() == 0 if coll else False
        is_onboarding = await asyncio.to_thread(check_onboarding)
    except Exception as e:
        logging.error(f"Onboarding check failed: {e}")
    
    # 2. Retrieve memories
    memories = []
    if message_text:
        memories = await asyncio.to_thread(memory_manager.search_memories, message_text)
    
    # 3. Get AI response (Gemini + Tools)
    ai_response = await get_ai_response(message_text, memories, is_onboarding, image)
    
    # 4. Send response with high resilience
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=60,
            read_timeout=60,
            write_timeout=60,
            pool_timeout=60
        )
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
    
    # 5. Background: Detect and save facts
    asyncio.create_task(detect_and_save_facts(message_text, ai_response, memory_manager))

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not (token and os.getenv("GEMINI_API_KEY")):
        print("Error: Required environment variables (TELEGRAM_BOT_TOKEN, GEMINI_API_KEY) missing.")
        exit(1)

    # Start health check server
    threading.Thread(target=run_health_server, daemon=True).start()

    # Correct request configuration: Timeouts go in HTTPXRequest
    request_config = HTTPXRequest(
        connect_timeout=120, 
        read_timeout=120, 
        write_timeout=120, 
        pool_timeout=120
    )
    
    application = ApplicationBuilder().token(token).request(request_config).build()
    application.add_error_handler(error_handler)
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message))
    
    print("--- ELIJAH VERSION 2.5 (FIXED-POLLING) IS STARTING ---")
    
    # Manual retry loop for initial connection
    while True:
        try:
            # run_polling only accepts 'timeout' (polling interval), not 'connect_timeout'
            application.run_polling(
                timeout=30,
                bootstrap_retries=-1
            )
            break
        except Exception as e:
            logging.error(f"Polling crashed, restarting in 10s... Error: {e}")
            time.sleep(10)
