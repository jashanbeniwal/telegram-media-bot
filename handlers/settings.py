from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from config import config
from database.operations import get_db_operations
from utils.premium import check_premium_status

logger = logging.getLogger(__name__)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    user_id = update.effective_user.id
    
    # Check premium status
    is_premium = await check_premium_status(user_id)
    
    # Get current settings
    db_ops = await get_db_operations()
    settings = await db_ops.get_user_settings(user_id)
    
    if not settings:
        await update.message.reply_text("❌ Failed to load settings. Please try again.")
        return
    
    # Create settings keyboard
    keyboard = [
        [InlineKeyboardButton(f"🔄 Bulk Mode: {settings.bulk_mode.upper()}", callback_data="set_bulk_mode")],
        [InlineKeyboardButton(f"🖼️ Thumbnail: {'ON' if settings.thumbnail_enabled else 'OFF'}", callback_data="set_thumbnail")],
        [InlineKeyboardButton(f"📝 Rename Files: {'ON' if settings.rename_files else 'OFF'}", callback_data="set_rename")],
        [InlineKeyboardButton(f"⬆️ Upload as: {settings.upload_mode.upper()}", callback_data="set_upload_mode")],
        [InlineKeyboardButton(f"📊 Video Metadata: {'ON' if settings.video_metadata else 'OFF'}", callback_data="set_metadata")],
        [InlineKeyboardButton("🎵 MP3 Tag Settings", callback_data="set_mp3_tags")],
        [InlineKeyboardButton("🔊 Audio Settings", callback_data="set_audio_settings")],
        [InlineKeyboardButton("🔄 Reset Settings", callback_data="set_reset")],
        [InlineKeyboardButton("❌ Close", callback_data="set_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Premium badge
    premium_text = "⭐ PREMIUM USER" if is_premium else "🆓 FREE USER"
    
    message_text = f"""
    ⚙️ **Settings Panel** ⚙️

    👤 User: {update.effective_user.first_name}
    📊 Status: {premium_text}
    
    Current Settings:
    • Bulk Mode: {settings.bulk_mode.upper()}
    • Thumbnail: {'✅ ON' if settings.thumbnail_enabled else '❌ OFF'}
    • Rename Files: {'✅ ON' if settings.rename_files else '❌ OFF'}
    • Upload as: {settings.upload_mode.upper()}
    • Video Metadata: {'✅ ON' if settings.video_metadata else '❌ OFF'}
    • Audio Speed: {settings.audio_speed}x
    • Audio Volume: {settings.audio_volume}%
    
    Click buttons to toggle settings.
    """
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    db_ops = await get_db_operations()
    settings = await db_ops.get_user_settings(user_id)
    
    if not settings:
        await query.edit_message_text("❌ Failed to load settings.")
        return
    
    if action == "set_bulk_mode":
        # Toggle bulk mode
        new_mode = "off" if settings.bulk_mode == "on" else "on"
        await db_ops.update_user_settings(user_id, bulk_mode=new_mode)
        
    elif action == "set_thumbnail":
        # Toggle thumbnail
        new_thumbnail = not settings.thumbnail_enabled
        await db_ops.update_user_settings(user_id, thumbnail_enabled=new_thumbnail)
        
    elif action == "set_rename":
        # Toggle rename
        new_rename = not settings.rename_files
        await db_ops.update_user_settings(user_id, rename_files=new_rename)
        
    elif action == "set_upload_mode":
        # Cycle through upload modes
        modes = ["video", "audio", "document"]
        current_index = modes.index(settings.upload_mode)
        next_mode = modes[(current_index + 1) % len(modes)]
        await db_ops.update_user_settings(user_id, upload_mode=next_mode)
        
    elif action == "set_metadata":
        # Toggle metadata
        new_metadata = not settings.video_metadata
        await db_ops.update_user_settings(user_id, video_metadata=new_metadata)
        
    elif action == "set_mp3_tags":
        # Show MP3 tag settings
        await show_mp3_tags_settings(query, settings)
        return
        
    elif action == "set_audio_settings":
        # Show audio settings
        await show_audio_settings(query, settings)
        return
        
    elif action == "set_reset":
        # Reset settings
        await db_ops.reset_user_settings(user_id)
        await query.edit_message_text("✅ Settings reset to default!")
        return
        
    elif action == "set_close":
        # Close settings
        await query.delete_message()
        return
    
    # Refresh settings display
    await settings_command(update, context)

async def show_mp3_tags_settings(query, settings):
    """Show MP3 tag settings panel"""
    keyboard = [
        [
            InlineKeyboardButton("Title", callback_data="mp3_title"),
            InlineKeyboardButton("Artist", callback_data="mp3_artist"),
        ],
        [
            InlineKeyboardButton("Album", callback_data="mp3_album"),
            InlineKeyboardButton("Year", callback_data="mp3_year"),
        ],
        [
            InlineKeyboardButton("Genre", callback_data="mp3_genre"),
            InlineKeyboardButton("Track", callback_data="mp3_track"),
        ],
        [
            InlineKeyboardButton("Cover Art", callback_data="mp3_cover"),
            InlineKeyboardButton("Clear All", callback_data="mp3_clear"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    tags_text = "\n".join([f"• {k}: {v}" for k, v in settings.mp3_tags.items()]) if settings.mp3_tags else "No tags set"
    
    message_text = f"""
    🎵 **MP3 Tag Settings**
    
    Current Tags:
    {tags_text}
    
    Click buttons to edit tags.
    """
    
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def show_audio_settings(query, settings):
    """Show audio settings panel"""
    keyboard = [
        [
            InlineKeyboardButton(f"Bitrate: {settings.audio_settings.get('bitrate', '192k')}", callback_data="audio_bitrate"),
            InlineKeyboardButton(f"Sample Rate: {settings.audio_settings.get('sample_rate', '44100')}Hz", callback_data="audio_sample"),
        ],
        [
            InlineKeyboardButton(f"Speed: {settings.audio_speed}x", callback_data="audio_speed"),
            InlineKeyboardButton(f"Volume: {settings.audio_volume}%", callback_data="audio_volume"),
        ],
        [
            InlineKeyboardButton(f"Compress: {'ON' if settings.compress_audio else 'OFF'}", callback_data="audio_compress"),
            InlineKeyboardButton(f"Quality: {settings.compress_quality}/10", callback_data="audio_quality"),
        ],
        [
            InlineKeyboardButton("Bass Boost", callback_data="audio_bass"),
            InlineKeyboardButton("Treble Boost", callback_data="audio_treble"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
    🔊 **Audio Settings**
    
    Current Settings:
    • Bitrate: {settings.audio_settings.get('bitrate', '192k')}
    • Sample Rate: {settings.audio_settings.get('sample_rate', '44100')}Hz
    • Channels: {settings.audio_settings.get('channels', 2)}
    • Speed: {settings.audio_speed}x
    • Volume: {settings.audio_volume}%
    • Compression: {'✅ ON' if settings.compress_audio else '❌ OFF'}
    • Quality: {settings.compress_quality}/10
    """
    
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
