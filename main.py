import os
import asyncio
import logging
import tempfile
import threading
import time
import httpx
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# --- ULTIMATE LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)

load_dotenv()

VERSION = "2.16 (INFINITE-BOOTSTRAP)"

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
        self.wfile.write(f"Elijah {VERSION} is waiting for network...".encode())
    def log_message(self, *args): pass

def run_health_server():
    port = int(os.getenv("PORT", 7860))
    try:
        httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logging.info(f"Health check live on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health server failed: {e}")

# --- BOT HANDLERS ---
memory_manager = None

async def error_handler(update, context):
    logging.error(f"GLOBAL ERROR: {context.error}")

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    logging.info(f"START command from {user_id}")
    await update.message.reply_text(f"Elijah {VERSION} is ONLINE!\nID: `{user_id}`")

async def handle_message(update, context):
    from PIL import Image
    from core.intelligence import get_ai_response, detect_and_save_facts
    
    if not update or not update.message: return
    user_id = str(update.effective_user.id)
    auth_id = sanitize(os.getenv("TELEGRAM_USER_ID", ""))
    
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
        msg = update.message.text or update.message.caption or "Analyze this"
        ai_response = await get_ai_response(msg, memories, is_onboarding, image)
        
        # Send with high-level retry
        for i in range(3):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=ai_response,
                    connect_timeout=60,
                    read_timeout=60
                )
                logging.info(f"Reply sent to {user_id}")
                break
            except Exception as e:
                logging.warning(f"Reply retry {i+1} failed: {e}")
                await asyncio.sleep(5)
                
        asyncio.create_task(detect_and_save_facts(msg, ai_response, memory_manager))
        
    except Exception as e:
        logging.error(f"Logic error: {e}", exc_info=True)
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

async def test_telegram_api(token):
    """Test if we can actually reach Telegram via HTTPS before starting the app."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    logging.info(f"Diagnostic: Testing HTTPS connection to Telegram...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                logging.info("Diagnostic SUCCESS: Telegram API is reachable via HTTPS.")
                return True
            else:
                logging.error(f"Diagnostic FAILED: Status {resp.status_code}. Content: {resp.text}")
                return False
    except Exception as e:
        logging.error(f"Diagnostic CRITICAL: Cannot reach Telegram API via HTTPS. Error: {e}")
        return False

async def main():
    logging.info(f"=== INITIALIZING ELIJAH {VERSION} ===")
    
    token = sanitize(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    auth_id = sanitize(os.getenv("TELEGRAM_USER_ID", ""))
    
    logging.info(f"TOKEN: {mask(token)}")
    logging.info(f"AUTH ID: {auth_id}")
    
    if not token:
        logging.critical("FATAL: No Token!")
        return

    # Start health server
    threading.Thread(target=run_health_server, daemon=True).start()

    from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
    from telegram.request import HTTPXRequest
    from core.memory import MemoryManager
    
    global memory_manager
    memory_manager = MemoryManager()
    
    # Configure Application with max timeouts
    request_config = HTTPXRequest(connect_timeout=120, read_timeout=120)
    application = ApplicationBuilder().token(token).request(request_config).build()
    
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logging.info("=== ENTERING BOOTSTRAP RETRY LOOP ===")
    
    retry_delay = 5
    while True:
        try:
            # 1. Manual network test
            if not await test_telegram_api(token):
                logging.warning(f"Network not ready. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)
                continue

            # 2. Try to initialize the application
            logging.info("Attempting application.initialize()...")
            await application.initialize()
            
            logging.info("Attempting application.start()...")
            await application.start()
            
            logging.info("Attempting application.updater.start_polling()...")
            await application.updater.start_polling(drop_pending_updates=True)
            
            logging.info(f"=== SUCCESS: ELIJAH {VERSION} IS FULLY ONLINE ===")
            break # Exit loop on success
            
        except Exception as e:
            logging.error(f"Bootstrap failure: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

    # Keep the async loop alive
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.critical(f"FATAL UNCAUGHT CRASH: {e}", exc_info=True)
