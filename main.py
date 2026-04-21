import os
import asyncio
import logging
import tempfile
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Configure logging to be extremely verbose for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

# Enable telegram library debug logs to see raw network traffic
logging.getLogger("telegram").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

load_dotenv()

VERSION = "2.9 (IDENTITY-CHECK)"

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Elijah {VERSION} is polling!".encode())
    
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
    logging.error(f"TELEGRAM ERROR: {context.error}")

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    logging.info(f"!!!! START COMMAND RECEIVED FROM: {user_id} !!!!")
    await update.message.reply_text(f"Elijah {VERSION} is online!\n\nI am listening. Your User ID is: {user_id}\n\nPlease confirm this ID is in your TELEGRAM_USER_ID environment variable.")

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update.message:
        return

    user_id = str(update.effective_user.id)
    message_text = update.message.text or update.message.caption or "[No Text]"
    logging.info(f"!!!! MESSAGE RECEIVED FROM {user_id}: {message_text} !!!!")
    
    authorized_user = os.getenv("TELEGRAM_USER_ID")
    if authorized_user and user_id != authorized_user:
        logging.warning(f"ACCESS DENIED: User {user_id} is not the authorized boss ({authorized_user})")
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
    logging.info(f"Generating AI response for {user_id}...")
    ai_response = await get_ai_response(message_text, memories, is_onboarding, image)
    
    # 4. Reply
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=60,
            read_timeout=60
        )
        logging.info(f"Reply successfully sent to {user_id}")
    except Exception as e:
        logging.error(f"Failed to send reply: {e}")
    
    # 5. Background Save
    asyncio.create_task(detect_and_save_facts(message_text, ai_response, memory_manager))

    if tmp_path and os.path.exists(tmp_path):
        os.remove(tmp_path)

async def heartbeat_logger():
    """Logs a message every 60 seconds to prove the event loop is running."""
    while True:
        logging.info("--- HEARTBEAT: Elijah is still polling for messages... ---")
        await asyncio.sleep(60)

async def main():
    logging.info(f"--- ELIJAH {VERSION} INITIALIZING ---")
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.critical("CRITICAL: TELEGRAM_BOT_TOKEN is missing!")
        return

    # Start health server
    threading.Thread(target=run_health_server, daemon=True).start()

    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
    from telegram.request import HTTPXRequest
    from core.memory import MemoryManager
    
    global memory_manager
    memory_manager = MemoryManager()
    
    logging.info("Building Telegram Application...")
    request_config = HTTPXRequest(connect_timeout=60, read_timeout=60)
    application = ApplicationBuilder().token(token).request(request_config).build()
    
    # Log Bot Identity
    me = await application.bot.get_me()
    logging.info(f"!!!! BOT IDENTITY: @{me.username} (ID: {me.id}) !!!!")
    logging.info("Verify this is the bot you are actually chatting with!")

    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    # Start heartbeat
    asyncio.create_task(heartbeat_logger())
    
    logging.info("Starting Polling loop (drop_pending_updates=True)...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Keep the script running
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"FATAL CRASH: {e}", exc_info=True)
