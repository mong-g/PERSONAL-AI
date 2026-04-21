import os
import asyncio
import logging
import tempfile
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Configure logging early
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

load_dotenv()

VERSION = "2.8 (STABLE-BOOTSTRAP)"

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Elijah {VERSION} is active!".encode())
    
    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.getenv("PORT", 7860))
    server_address = ('0.0.0.0', port)
    try:
        httpd = HTTPServer(server_address, HealthCheckHandler)
        logging.info(f"Health check server starting on port {port}...")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health check server failed: {e}")

# Global placeholder
memory_manager = None

async def error_handler(update: object, context):
    logging.error(f"Telegram Bot Error: {context.error}")

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    logging.info(f"START command from: {user_id}")
    await update.message.reply_text(f"Elijah {VERSION} is online!\nYour User ID: {user_id}")

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update.message:
        return

    user_id = str(update.effective_user.id)
    message_text = update.message.text or update.message.caption or "[No Text]"
    logging.info(f"Message from {user_id}: {message_text}")
    
    authorized_user = os.getenv("TELEGRAM_USER_ID")
    if authorized_user and user_id != authorized_user:
        logging.warning(f"Blocked unauthorized user: {user_id}")
        return

    image = None
    tmp_path = None

    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
                await photo_file.download_to_drive(tmp_path)
                image = Image.open(tmp_path)
        except Exception as e:
            logging.error(f"Photo error: {e}")

    # 1. Onboarding
    is_onboarding = False
    try:
        def check():
            coll = memory_manager.get_collection()
            return coll.count() == 0 if coll else False
        is_onboarding = await asyncio.to_thread(check)
    except Exception:
        pass
    
    # 2. Memories
    memories = []
    if update.message.text:
        memories = await asyncio.to_thread(memory_manager.search_memories, update.message.text)
    
    # 3. AI
    ai_response = await get_ai_response(message_text, memories, is_onboarding, image)
    
    # 4. Reply
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=60,
            read_timeout=60
        )
    except Exception as e:
        logging.error(f"Reply failed: {e}")
    
    # 5. Background Save
    asyncio.create_task(detect_and_save_facts(message_text, ai_response, memory_manager))

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

if __name__ == '__main__':
    logging.info(f"--- ELIJAH {VERSION} STARTING ---")
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.critical("Missing TELEGRAM_BOT_TOKEN")
        exit(1)

    # Health check
    threading.Thread(target=run_health_server, daemon=True).start()

    # Move heavy imports and init here
    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
    from telegram.request import HTTPXRequest
    from core.memory import MemoryManager
    
    memory_manager = MemoryManager()
    
    # High-timeout configuration to survive bootstrap on HF
    logging.info("Configuring Application with high timeouts...")
    request_config = HTTPXRequest(connect_timeout=60, read_timeout=60)
    
    application = ApplicationBuilder().token(token).request(request_config).build()
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logging.info("Starting Polling loop...")
    # Infinite retries for the initial 'get_me' call
    application.run_polling(drop_pending_updates=True, bootstrap_retries=-1)
