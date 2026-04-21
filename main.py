import os
import asyncio
import logging
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

load_dotenv()

VERSION = "2.12 (WEBHOOK-RESET)"

# --- HELPERS ---
def mask(s):
    if not s: return "MISSING"
    return f"{s[:5]}...{s[-3:]}" if len(s) > 8 else "***"

# --- HEALTH SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Elijah {VERSION} is polling successfully!".encode())
    def log_message(self, *args): pass

def run_health_server():
    port = int(os.getenv("PORT", 7860))
    try:
        httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logging.info(f"Health check live on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health server error: {e}")

# --- BOT HANDLERS ---
memory_manager = None

async def handle_any_update(update, context):
    """Raw logger for every single thing Telegram sends us."""
    logging.info(f"--- RAW UPDATE DETECTED --- Type: {type(update).__name__}")

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    logging.info(f"START received from {user_id}")
    await update.message.reply_text(f"Elijah {VERSION} is ACTIVE.\n\nYour ID: `{user_id}`\nAuthorized ID: `{os.getenv('TELEGRAM_USER_ID')}`")

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update.message: return
    
    user_id = str(update.effective_user.id)
    auth_id = str(os.getenv("TELEGRAM_USER_ID", ""))
    
    logging.info(f"CHAT from {user_id}: {update.message.text or '[Media]'}")
    
    if auth_id and user_id != auth_id:
        logging.warning(f"UNAUTHORIZED ACCESS: User {user_id} is not {auth_id}")
        return

    image, tmp_path = None, None
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
                await photo_file.download_to_drive(tmp_path)
                image = Image.open(tmp_path)
        except Exception as e:
            logging.error(f"Image error: {e}")

    try:
        def get_mem():
            coll = memory_manager.get_collection()
            m = []
            if update.message.text:
                m = memory_manager.search_memories(update.message.text)
            return m, (coll.count() == 0 if coll else False)
        
        memories, is_onboarding = await asyncio.to_thread(get_mem)
        msg = update.message.text or update.message.caption or "Look at this."
        ai_response = await get_ai_response(msg, memories, is_onboarding, image)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=60,
            read_timeout=60
        )
        asyncio.create_task(detect_and_save_facts(msg, ai_response, memory_manager))
        
    except Exception as e:
        logging.error(f"Processing error: {e}", exc_info=True)
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

async def main():
    logging.info(f"=== INITIALIZING ELIJAH {VERSION} ===")
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    auth_id = os.getenv("TELEGRAM_USER_ID")
    
    logging.info(f"TOKEN: {mask(token)}")
    logging.info(f"AUTH ID: {auth_id}")
    
    if not token:
        logging.critical("FATAL: No Bot Token!")
        return

    threading.Thread(target=run_health_server, daemon=True).start()

    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, TypeHandler, filters
    from telegram.request import HTTPXRequest
    from core.memory import MemoryManager
    
    global memory_manager
    memory_manager = MemoryManager()
    
    # 1. Reset Telegram State
    logging.info("CLEANING TELEGRAM STATE (Deleting Webhooks)...")
    temp_app = ApplicationBuilder().token(token).build()
    await temp_app.bot.delete_webhook(drop_pending_updates=True)
    await temp_app.shutdown()
    logging.info("TELEGRAM STATE CLEANED. Ready for Polling.")

    # 2. Build Real Application
    request_config = HTTPXRequest(connect_timeout=120, read_timeout=120)
    application = ApplicationBuilder().token(token).request(request_config).build()
    
    application.add_handler(TypeHandler(object, handle_any_update), group=-1) 
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logging.info(f"=== ELIJAH {VERSION} STARTING POLLING ===")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt: pass
    except Exception as e:
        logging.critical(f"FATAL CRASH: {e}", exc_info=True)
