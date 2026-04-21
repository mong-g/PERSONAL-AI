import os
import asyncio
import logging
import tempfile
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Force logging to be verbose
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

load_dotenv()

VERSION = "2.7 (DEEP-DIAGNOSTIC)"

# --- Simple Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Elijah is alive and watching everything!")
    
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

memory_manager = None

async def error_handler(update: object, context):
    logging.error(f"BOT ERROR: {context.error}")

async def start_command(update, context):
    """Specific handler for the /start command."""
    user_id = str(update.effective_user.id)
    logging.info(f"START command received from user: {user_id}")
    await update.message.reply_text(f"Elijah {VERSION} is online! I'm ready to chat. Your User ID is: {user_id}")

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update.message:
        return

    user_id = str(update.effective_user.id)
    message_text = update.message.text or update.message.caption or "[No Text]"
    
    logging.info(f"MESSAGE RECEIVED from {user_id}: {message_text}")
    
    authorized_user = os.getenv("TELEGRAM_USER_ID")
    if authorized_user and user_id != authorized_user:
        logging.warning(f"BLOCKED: User {user_id} is not authorized (Expected {authorized_user})")
        return

    image = None
    tmp_path = None

    if update.message.photo:
        logging.info(f"Processing photo from {user_id}")
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
                await photo_file.download_to_drive(tmp_path)
                image = Image.open(tmp_path)
        except Exception as e:
            logging.error(f"Error downloading photo: {e}")

    # 1. Onboarding Check (Lazy)
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
    if update.message.text:
        memories = await asyncio.to_thread(memory_manager.search_memories, update.message.text)
    
    # 3. Get AI response
    logging.info(f"Thinking for user {user_id}...")
    ai_response = await get_ai_response(message_text, memories, is_onboarding, image)
    
    # 4. Send response
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=30,
            read_timeout=30
        )
        logging.info(f"REPLY SENT to {user_id}")
    except Exception as e:
        logging.error(f"Failed to send reply to {user_id}: {e}")
    
    # 5. Background: Save facts
    asyncio.create_task(detect_and_save_facts(message_text, ai_response, memory_manager))

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

if __name__ == '__main__':
    logging.info(f"--- INITIALIZING ELIJAH {VERSION} ---")
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.critical("CRITICAL: TELEGRAM_BOT_TOKEN is missing!")
        exit(1)

    # Start health server
    threading.Thread(target=run_health_server, daemon=True).start()

    # Deferred imports
    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
    from core.memory import MemoryManager
    
    memory_manager = MemoryManager()
    
    logging.info("Building Application...")
    application = ApplicationBuilder().token(token).build()
    
    # Handlers
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logging.info(f"--- ELIJAH {VERSION} IS POLLING ---")
    application.run_polling(drop_pending_updates=True)
