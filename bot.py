import asyncio
import logging
from typing import Dict, Any
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

from config import config
from database.connection import get_database
from database.operations import init_user_settings, get_user_settings
from handlers.start import start_command, help_command
from handlers.settings import settings_command, settings_callback
from handlers.video import video_handler, video_callback
from handlers.audio import audio_handler, audio_callback
from handlers.document import document_handler, document_callback
from handlers.bulk import bulk_handler, bulk_callback
from handlers.callback import handle_callback
from utils.premium import check_premium_status, apply_wait_time
from utils.helpers import cleanup_temp_files

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramMediaBot:
    def __init__(self):
        self.application = None
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
    async def init_db(self):
        """Initialize database connection"""
        try:
            db = await get_database()
            logger.info("Database connection established")
            return db
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the bot"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            # Notify user about error
            if update.effective_chat:
                await update.effective_chat.send_message(
                    "❌ An error occurred while processing your request. Please try again later."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def check_user_limit(self, user_id: int) -> bool:
        """Check if user has reached concurrent job limit"""
        user_jobs = sum(1 for session in self.user_sessions.values() 
                       if session.get('user_id') == user_id and session.get('processing'))
        return user_jobs < config.MAX_CONCURRENT_JOBS
    
    async def download_progress(self, current, total, update, context, file_type):
        """Handle download progress updates"""
        try:
            progress = (current / total) * 100
            if int(progress) % 10 == 0:  # Update every 10%
                await update.effective_chat.send_message(
                    f"⬇️ Downloading {file_type}: {progress:.1f}%"
                )
        except Exception as e:
            logger.error(f"Error in download progress: {e}")
    
    async def upload_progress(self, current, total, update, context, file_type):
        """Handle upload progress updates"""
        try:
            progress = (current / total) * 100
            if int(progress) % 10 == 0:  # Update every 10%
                await update.effective_chat.send_message(
                    f"⬆️ Uploading {file_type}: {progress:.1f}%"
                )
        except Exception as e:
            logger.error(f"Error in upload progress: {e}")
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("settings", settings_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(
            filters.VIDEO | filters.VIDEO_NOTE, video_handler
        ))
        self.application.add_handler(MessageHandler(
            filters.AUDIO | filters.VOICE, audio_handler
        ))
        self.application.add_handler(MessageHandler(
            filters.Document.ALL, document_handler
        ))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(handle_callback, pattern="^settings_"))
        self.application.add_handler(CallbackQueryHandler(video_callback, pattern="^video_"))
        self.application.add_handler(CallbackQueryHandler(audio_callback, pattern="^audio_"))
        self.application.add_handler(CallbackQueryHandler(document_callback, pattern="^doc_"))
        self.application.add_handler(CallbackQueryHandler(bulk_callback, pattern="^bulk_"))
        self.application.add_handler(CallbackQueryHandler(settings_callback, pattern="^set_"))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def cleanup(self):
        """Cleanup resources"""
        await cleanup_temp_files()
        logger.info("Cleanup completed")
    
    async def run_webhook(self):
        """Run bot with webhook (for Koyeb)"""
        await self.application.bot.set_webhook(
            url=f"{config.WEBHOOK_URL}/{config.BOT_TOKEN}",
            drop_pending_updates=True
        )
        
        # Start web server
        from fastapi import FastAPI, Request
        import uvicorn
        
        app = FastAPI()
        
        @app.post(f"/{config.BOT_TOKEN}")
        async def process_webhook(request: Request):
            data = await request.json()
            update = Update.de_json(data, self.application.bot)
            await self.application.process_update(update)
            return {"status": "ok"}
        
        @app.get("/")
        async def health_check():
            return {"status": "healthy", "bot": config.BOT_USERNAME}
        
        config = uvicorn.Config(
            app,
            host=config.HOST,
            port=config.PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def run_polling(self):
        """Run bot with polling (for development)"""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running
        await asyncio.Event().wait()
    
    async def start(self, use_webhook: bool = False):
        """Start the bot"""
        # Initialize database
        await self.init_db()
        
        # Create Application
        self.application = Application.builder() \
            .token(config.BOT_TOKEN) \
            .concurrent_updates(True) \
            .build()
        
        # Setup handlers
        self.setup_handlers()
        
        # Start bot
        if use_webhook and config.WEBHOOK_URL:
            logger.info("Starting bot with webhook...")
            await self.run_webhook()
        else:
            logger.info("Starting bot with polling...")
            await self.run_polling()

async def main():
    """Main entry point"""
    bot = TelegramMediaBot()
    
    try:
        # Check if webhook should be used
        use_webhook = bool(config.WEBHOOK_URL)
        await bot.start(use_webhook=use_webhook)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
