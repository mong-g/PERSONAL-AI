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

VERSION = "2.14 (LOOP-FIX)"

# --- CONFIG ---
def mask(s):
    if not s: return "MISSING"
    return f"{s[:5]}...{s[-3:]}" if len(s) > 8 else "***"

# --- HEALTH SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Elijah {VERSION} is active!".encode())
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
    logging.info(f"--- UPDATE: {type(update).__name__} ---")

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    logging.info(f"START from {user_id}")
    await update.message.reply_text(f"Elijah {VERSION} online!\nID: `{user_id}`")

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update.message: return
    user_id = str(update.effective_user.id)
    auth_id = str(os.getenv("TELEGRAM_USER_ID", ""))
    
    if auth_id and user_id != auth_id:
        logging.warning(f"UNAUTHORIZED: {user_id}")
        return

    logging.info(f"MSG from {user_id}")
    
    image, tmp_path = None, None
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
                await photo_file.download_to_drive(tmp_path)
                image = Image.open(tmp_path)
        except Exception as e: logging.error(f"Img err: {e}")

    try:
        def get_mem():
            coll = memory_manager.get_collection()
            m = memory_manager.search_memories(update.message.text) if update.message.text else []
            return m, (coll.count() == 0 if coll else False)
        
        memories, is_onboarding = await asyncio.to_thread(get_mem)
        msg = update.message.text or update.message.caption or "Image"
        ai_response = await get_ai_response(msg, memories, is_onboarding, image)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=ai_response,
            connect_timeout=60,
            read_timeout=60
        )
        asyncio.create_task(detect_and_save_facts(msg, ai_response, memory_manager))
    except Exception as e: logging.error(f"Proc err: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

async def main():
    logging.info(f"=== INITIALIZING ELIJAH {VERSION} ===")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: 
        logging.critical("No Token!")
        return

    # Start health server immediately
    threading.Thread(target=run_health_server, daemon=True).start()

    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, TypeHandler, filters
    from telegram.request import HTTPXRequest
    from core.memory import MemoryManager
    
    global memory_manager
    memory_manager = MemoryManager()
    
    # EXTREME TIMEOUT CONFIG
    request_config = HTTPXRequest(connect_timeout=120, read_timeout=120)

    # 1. Non-fatal Reset
    logging.info("Step 1: Attempting Webhook Cleanup (Non-fatal)...")
    try:
        cleanup_bot = ApplicationBuilder().token(token).request(request_config).build().bot
        await cleanup_bot.delete_webhook(drop_pending_updates=True)
        logging.info("Step 1 SUCCESS: Webhook deleted.")
    except Exception as e:
        logging.warning(f"Step 1 SKIPPED: {e}")
    
    # 2. Build Main Application
    logging.info("Step 2: Building Application...")
    application = ApplicationBuilder().token(token).request(request_config).build()
    application.add_handler(TypeHandler(object, handle_any_update), group=-1) 
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logging.info(f"=== Step 3: STARTING POLLING ({VERSION}) ===")
    
    # Manual start sequence to avoid loop conflicts
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    logging.info("Polling successfully started. Elijah is online.")
    
    # Keep the async loop alive
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    # Use a simpler execution to avoid nested run_polling errors
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.critical(f"FATAL CRASH: {e}", exc_info=True)
