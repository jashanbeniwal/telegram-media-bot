import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import db

# Load handlers
from handlers.video_handlers import *
from handlers.audio_handlers import *
from handlers.utility_handlers import *
from handlers.admin_handlers import *

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class MediaBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        # Start command
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("credits", self.credits))
        
        # Video handlers
        self.application.add_handler(CommandHandler("thumbnail", thumbnail_command))
        self.application.add_handler(CommandHandler("trim", trim_command))
        self.application.add_handler(CommandHandler("merge", merge_command))
        self.application.add_handler(CommandHandler("split", split_command))
        self.application.add_handler(CommandHandler("screenshot", screenshot_command))
        self.application.add_handler(CommandHandler("optimize", optimize_command))
        
        # Audio handlers
        self.application.add_handler(CommandHandler("extract_audio", extract_audio_command))
        self.application.add_handler(CommandHandler("remove_audio", remove_audio_command))
        self.application.add_handler(CommandHandler("convert_audio", convert_audio_command))
        self.application.add_handler(CommandHandler("video_to_audio", video_to_audio_command))
        
        # Utility handlers
        self.application.add_handler(CommandHandler("caption", caption_command))
        self.application.add_handler(CommandHandler("metadata", metadata_command))
        self.application.add_handler(CommandHandler("subtitle", subtitle_command))
        self.application.add_handler(CommandHandler("archive", archive_command))
        
        # Admin handlers
        self.application.add_handler(CommandHandler("admin", admin_command))
        self.application.add_handler(CommandHandler("add_credits", add_credits_command))
        self.application.add_handler(CommandHandler("set_premium", set_premium_command))
        
        # File handlers
        self.application.add_handler(MessageHandler(
            filters.VIDEO | filters.Document.VIDEO, 
            handle_video
        ))
        self.application.add_handler(MessageHandler(
            filters.AUDIO | filters.Document.AUDIO,
            handle_audio
        ))
        self.application.add_handler(MessageHandler(
            filters.Document.ALL,
            handle_document
        ))
        
        # Callback queries for interactive features
        self.application.add_handler(CallbackQueryHandler(button_handler))
    
    async def start(self, update, context):
        user = update.effective_user
        user_data = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        
        # Create user if not exists
        existing_user = await db.get_user(user.id)
        if not existing_user:
            await db.create_user(user_data)
            await update.message.reply_text("🎉 Welcome! You've been given 10 free credits to start!")
        else:
            await db.db.users.update_one(
                {"user_id": user.id},
                {"$set": {"last_activity": datetime.now(pytz.UTC)}}
            )
        
        user_info = await db.get_user(user.id)
        credits = user_info['credits']
        premium_status = "💎 Premium" if user_info.get('is_premium') else "🔓 Free"
        
        welcome_text = f"""
🤖 **Media Processing Bot**

👤 **User:** {user.first_name}
{premium_status} | 🪙 Credits: {credits}

🎯 **Available Features:**

🎥 **Video Tools:**
• 📸 Extract Thumbnails - `/thumbnail`
• ✂️ Trim Videos - `/trim start_time end_time`
• 🔗 Merge Videos - `/merge`
• 🪚 Split Videos - `/split segment_time`
• 📷 Take Screenshots - `/screenshot time1,time2,...`
• ⚡ Optimize Videos - `/optimize quality(high/medium/low)`

🔊 **Audio Tools:**
• 🎵 Extract Audio from video - `/extract_audio`
• 🔇 Remove Audio from video - `/remove_audio`
• 🔄 Convert Audio format - `/convert_audio format`
• 🎬 Video to Audio - `/video_to_audio`

📝 **Utilities:**
• ✏️ Edit Metadata - `/metadata`
• 📜 Manage Subtitles - `/subtitle`
• 📦 Create Archives - `/archive`

💎 **Premium Features:**
• Faster processing
• Higher quality outputs
• Larger file sizes
• Priority processing

Use `/help command` for detailed instructions.
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help(self, update, context):
        if context.args:
            command = context.args[0].lower()
            help_texts = {
                'thumbnail': '📸 Send a video and I will extract a thumbnail from it',
                'trim': '✂️ Format: /trim HH:MM:SS HH:MM:SS\\nExample: /trim 00:00:10 00:00:30',
                'merge': '🔗 Send multiple videos one by one, then type /done',
                'split': '🪚 Format: /split HH:MM:SS\\nExample: /split 00:05:00 (splits into 5min segments)',
                'screenshot': '📷 Format: /screenshot time1,time2,...\\nExample: /screenshot 00:01:00,00:02:30',
                'optimize': '⚡ Format: /optimize quality\\nQuality: high, medium, low',
                'extract_audio': '🎵 Send a video to extract audio from it',
                'remove_audio': '🔇 Send a video to remove audio track',
                'convert_audio': '🔄 Format: /convert_audio format\\nFormats: mp3, wav, aac, ogg',
                'video_to_audio': '🎬 Convert video file to audio file',
                'metadata': '📊 View and edit video metadata',
                'subtitle': '📜 Add or extract subtitles',
                'archive': '📦 Create zip archives from multiple files'
            }
            text = help_texts.get(command, f"No help available for {command}")
        else:
            text = "Use `/help command_name` for specific help. Available commands: thumbnail, trim, merge, split, screenshot, optimize, extract_audio, remove_audio, convert_audio, video_to_audio, metadata, subtitle, archive"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def credits(self, update, context):
        user = await db.get_user(update.effective_user.id)
        if user:
            credits = user['credits']
            premium = "💎 Premium User" if user.get('is_premium') else "🔓 Free User"
            await update.message.reply_text(f"{premium}\\n🪙 Available credits: {credits}")
        else:
            await update.message.reply_text("Please use /start first")
    
    def run(self):
        self.application.run_polling()

if __name__ == "__main__":
    bot = MediaBot()
    bot.run()
