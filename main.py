import os
import asyncio
import logging
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# --- ULTIMATE LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

load_dotenv()

VERSION = "2.15 (CLEAN-COMM)"

# --- HELPERS ---
def mask(s):
    if not s: return "MISSING"
    return f"{s[:5]}...{s[-3:]}" if len(s) > 8 else "***"

def sanitize(s):
    return "".join(s.split()) if s else ""

# --- HEALTH SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Elijah {VERSION} is operational.".encode())
    def log_message(self, *args): pass

def run_health_server():
    port = int(os.getenv("PORT", 7860))
    try:
        httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logging.info(f"Health server on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health server error: {e}")

# --- BOT HANDLERS ---
memory_manager = None

async def error_handler(update: object, context):
    logging.error(f"GLOBAL BOT ERROR: {context.error}")

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    logging.info(f"START received from {user_id}")
    
    # Retry logic for sending messages
    for i in range(3):
        try:
            await update.message.reply_text(f"Elijah {VERSION} is online!\nYour ID: `{user_id}`")
            logging.info(f"START reply sent to {user_id}")
            return
        except Exception as e:
            logging.warning(f"START reply retry {i+1} failed: {e}")
            await asyncio.sleep(2)

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update or not update.message: return
    user_id = str(update.effective_user.id)
    auth_id = sanitize(os.getenv("TELEGRAM_USER_ID", ""))
    
    if auth_id and user_id != auth_id:
        logging.warning(f"UNAUTHORIZED ACCESS: User {user_id} tried to chat.")
        return

    logging.info(f"MSG from {user_id}")
    
    # Image handling
    image, tmp_path = None, None
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
                await photo_file.download_to_drive(tmp_path)
                image = Image.open(tmp_path)
        except Exception as e: logging.error(f"Image error: {e}")

    # AI Processing
    try:
        def get_mem():
            coll = memory_manager.get_collection()
            m = memory_manager.search_memories(update.message.text) if update.message.text else []
            return m, (coll.count() == 0 if coll else False)
        
        memories, is_onboarding = await asyncio.to_thread(get_mem)
        msg = update.message.text or update.message.caption or "Look at this."
        ai_response = await get_ai_response(msg, memories, is_onboarding, image)
        
        # Send Reply with retry
        for i in range(3):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=ai_response,
                    connect_timeout=30,
                    read_timeout=30
                )
                logging.info(f"REPLY sent to {user_id}")
                break
            except Exception as e:
                logging.warning(f"REPLY retry {i+1} failed: {e}")
                await asyncio.sleep(2)
                
        asyncio.create_task(detect_and_save_facts(msg, ai_response, memory_manager))
        
    except Exception as e:
        logging.error(f"Processing error: {e}", exc_info=True)
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

async def main():
    logging.info(f"=== INITIALIZING ELIJAH {VERSION} ===")
    
    token = sanitize(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    auth_id = sanitize(os.getenv("TELEGRAM_USER_ID", ""))
    
    logging.info(f"TOKEN: {mask(token)}")
    logging.info(f"AUTH ID: {auth_id}")
    
    if not token:
        logging.critical("CRITICAL: BOT TOKEN MISSING!")
        return

    # Background health server
    threading.Thread(target=run_health_server, daemon=True).start()

    # Heavy imports
    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
    from telegram.request import HTTPXRequest
    from core.memory import MemoryManager
    
    global memory_manager
    memory_manager = MemoryManager()
    
    # Configure Application
    request_config = HTTPXRequest(connect_timeout=45, read_timeout=45)
    application = ApplicationBuilder().token(token).request(request_config).build()
    
    # Handlers
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logging.info(f"=== STARTING ELIJAH {VERSION} POLLING ===")
    
    # run_polling handles the entire lifecycle safely
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    logging.info("ELIJAH IS ONLINE.")
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
    except Exception as e:
        logging.critical(f"FATAL CRASH: {e}", exc_info=True)
