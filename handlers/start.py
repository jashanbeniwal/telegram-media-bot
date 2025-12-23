from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.operations import DatabaseOperations
from utils.premium import is_premium_user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Check if user exists
    db_user = await DatabaseOperations.get_user(user.id)
    if not db_user:
        await DatabaseOperations.create_user(user.id, user.username, user.first_name)
    
    # Get premium status
    premium = await is_premium_user(user.id)
    
    # Welcome message
    welcome_text = f"""
    🎉 *Welcome to Media Bot* 🎉

    👤 *User*: {user.first_name}
    📊 *Status*: {'⭐ PREMIUM' if premium else '🆓 FREE'}
    
    *Features Available*:
    • 🎥 Video Processing (Trim, Merge, Convert, etc.)
    • 🎵 Audio Processing (Effects, Convert, Edit, etc.)
    • 📄 Document Processing (Rename, Archive, Convert)
    • 🔄 Bulk Operations
    • ⚙️ Custom Settings
    
    *Commands*:
    /start - Start the bot
    /settings - Configure bot settings
    /help - Show help
    
    *How to use*:
    1. Send a video, audio, or document
    2. Choose from available options
    3. Process and download!
    
    ⚠️ *Limits*:
    Free: 500MB/file, 30min wait
    Premium: 2GB/file, no wait
    """
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("🎥 Video Guide", callback_data="guide_video"),
         InlineKeyboardButton("🎵 Audio Guide", callback_data="guide_audio")],
        [InlineKeyboardButton("📄 Document Guide", callback_data="guide_document"),
         InlineKeyboardButton("🔄 Bulk Guide", callback_data="guide_bulk")],
        [InlineKeyboardButton("⭐ Upgrade to Premium", callback_data="upgrade_premium")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
    *📖 Help Guide*
    
    *Video Features*:
    • Trim, Split, Merge videos
    • Extract audio/subtitles
    • Convert formats (MP4, MKV, AVI, etc.)
    • Optimize/compress videos
    • Generate thumbnails
    • Create GIFs
    
    *Audio Features*:
    • Convert formats (MP3, WAV, FLAC, etc.)
    • Apply effects (8D, Reverb, Equalizer)
    • Trim, Merge audio files
    • Adjust speed/volume
    • Edit MP3 tags
    • Compress audio
    
    *Document Features*:
    • Rename files
    • Create/extract archives
    • Convert subtitles
    • Format JSON
    • Remove forwarded tag
    
    *Bulk Operations*:
    • Process multiple files
    • Batch convert/rename
    • Bulk archive creation
    
    *Settings*:
    • Toggle bulk mode
    • Enable/disable thumbnails
    • Set upload preferences
    • Configure audio quality
    • Reset settings
    
    *Need more help?* Contact @admin
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")
