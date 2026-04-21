import os
import asyncio
import logging
import tempfile
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Force logging to be verbose and flushed
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

load_dotenv()

# Version tracking
VERSION = "2.6 (DIAGNOSTIC)"

# --- Simple Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Elijah {VERSION} is alive!".encode())
    
    def log_message(self, format, *args):
        return

def run_health_server():
    # Hugging Face usually expects port 7860
    port = int(os.getenv("PORT", 7860))
    server_address = ('0.0.0.0', port)
    try:
        httpd = HTTPServer(server_address, HealthCheckHandler)
        logging.info(f"Health check server starting on {server_address[0]}:{port}...")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health check server failed: {e}")

# Global placeholder for the memory manager
memory_manager = None

async def error_handler(update: object, context):
    logging.error("Exception while handling an update:", exc_info=context.error)
    if "Timed out" in str(context.error):
        return
        
    if update and hasattr(update, 'effective_chat') and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Elijah: I'm having a bit of a connection hiccup. One sec!"
            )
        except Exception:
            pass

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
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
    if message_text:
        memories = await asyncio.to_thread(memory_manager.search_memories, message_text)
    
    # 3. Get AI response
    ai_response = await get_ai_response(message_text, memories, is_onboarding, image)
    
    # 4. Send response
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=30,
            read_timeout=30
        )
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
    
    # 5. Background: Save facts
    asyncio.create_task(detect_and_save_facts(message_text, ai_response, memory_manager))

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

def test_connectivity():
    """Diagnostic tool to check if the container can reach external servers."""
    targets = [("api.telegram.org", 443), ("generativelanguage.googleapis.com", 443), ("google.com", 443)]
    for host, port in targets:
        try:
            socket.create_connection((host, port), timeout=5)
            logging.info(f"Connectivity check: PASSED reaching {host}")
        except Exception as e:
            logging.warning(f"Connectivity check: FAILED reaching {host}. Error: {e}")

if __name__ == '__main__':
    logging.info(f"--- ELIJAH VERSION {VERSION} IS INITIALIZING ---")
    
    # Test network immediately
    test_connectivity()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not (token and os.getenv("GEMINI_API_KEY")):
        logging.critical("Missing required environment variables (TELEGRAM_BOT_TOKEN or GEMINI_API_KEY).")
        exit(1)

    # Start health server in background
    threading.Thread(target=run_health_server, daemon=True).start()

    # Deferred imports to speed up initialization
    logging.info("Loading heavy dependencies...")
    from telegram.ext import ApplicationBuilder, MessageHandler, filters
    from core.memory import MemoryManager
    
    memory_manager = MemoryManager()
    
    logging.info("Building Telegram application...")
    application = ApplicationBuilder().token(token).build()
    application.add_error_handler(error_handler)
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message))
    
    logging.info(f"--- ELIJAH VERSION {VERSION} IS STARTING POLLING ---")
    
    while True:
        try:
            # Simple polling with automatic retries for bootstrap
            application.run_polling(
                timeout=30,
                bootstrap_retries=-1
            )
            break
        except Exception as e:
            logging.error(f"Polling crash detected. Restarting in 10s... Error: {e}")
            time.sleep(10)
