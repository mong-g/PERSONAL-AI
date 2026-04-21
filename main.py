import os
import asyncio
import logging
import tempfile
import threading
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

# --- Simple Health Check Server for Koyeb ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Elijah is alive!")
    
    # Suppress log messages to keep console clean
    def log_message(self, format, *args):
        return

def run_health_server():
    # Expose port 8000 for Koyeb health checks
    port = int(os.getenv("PORT", 8000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logging.info(f"Health check server starting on port {port}...")
    httpd.serve_forever()

memory_manager = MemoryManager()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logging.error("Exception while handling an update:", exc_info=context.error)
    if update and isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Elijah: Oops! I encountered a temporary network issue. Please try again in a moment."
            )
        except Exception:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    authorized_user = os.getenv("TELEGRAM_USER_ID")
    
    # Security: Only respond to the authorized user
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
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Elijah: I had trouble seeing that photo. Could you try sending it again?")
            return
    else:
        logging.info(f"Received message from {user_id}: {message_text}")

    # 1. Check for onboarding (ULTRA SAFE)
    is_onboarding = False
    try:
        # Wrap the whole check in thread to avoid any blocking
        def check_onboarding():
            if hasattr(memory_manager, 'get_collection'):
                coll = memory_manager.get_collection()
                if coll:
                    return coll.count() == 0
            return False
        
        is_onboarding = await asyncio.to_thread(check_onboarding)
    except Exception as e:
        logging.error(f"Onboarding check failed: {e}")
    
    # 2. Retrieve memories
    memories = []
    if message_text:
        # Wrap sync search in to_thread
        memories = await asyncio.to_thread(memory_manager.search_memories, message_text)
    
    # 3. Get AI response (Gemini + Tools) - NOW ASYNC
    ai_response = await get_ai_response(message_text, memories, is_onboarding, image)
    
    # 4. Send response with a longer timeout to handle flaky networks
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=30,
            read_timeout=30
        )
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
    
    # 5. Background: Detect and save facts - NOW ASYNC
    asyncio.create_task(detect_and_save_facts(message_text, ai_response, memory_manager))

    # Cleanup image
    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not (token and os.getenv("GEMINI_API_KEY")):
        print("Error: Required environment variables (TELEGRAM_BOT_TOKEN, GEMINI_API_KEY) missing.")
        exit(1)

    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Increase timeouts for flaky networks (Koyeb/HuggingFace/Spaces)
    request_config = HTTPXRequest(connect_timeout=30, read_timeout=30)
    application = ApplicationBuilder().token(token).request(request_config).build()
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Handle both text and photos
    message_handler = MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message)
    application.add_handler(message_handler)
    
    print("--- ELIJAH VERSION 2.2 (STABLE) IS STARTING ---")
    application.run_polling(connect_timeout=30, read_timeout=30)
