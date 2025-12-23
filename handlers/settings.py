from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.operations import DatabaseOperations, UserSettings
from utils.premium import is_premium_user

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings panel"""
    user_id = update.effective_user.id
    
    # Get current settings
    settings_data = await DatabaseOperations.get_user_settings(user_id)
    if not settings_data:
        await DatabaseOperations.init_user_settings(user_id)
        settings_data = await DatabaseOperations.get_user_settings(user_id)
    
    # Check premium
    premium = await is_premium_user(user_id)
    
    # Create settings message
    settings_text = f"""
    ⚙️ *Settings Panel*

    👤 User: {update.effective_user.first_name}
    📊 Status: {'⭐ PREMIUM' if premium else '🆓 FREE'}
    
    *Current Settings*:
    • 🔄 Bulk Mode: `{settings_data.bulk_mode.upper()}`
    • 🖼️ Thumbnail: `{'ON' if settings_data.thumbnail else 'OFF'}`
    • 📝 Rename Files: `{'ON' if settings_data.rename_files else 'OFF'}`
    • ⬆️ Upload as: `{settings_data.upload_mode.upper()}`
    • 📊 Video Metadata: `{'ON' if settings_data.video_metadata else 'OFF'}`
    • 🔊 Audio Bitrate: `{settings_data.audio_bitrate}`
    • 🎚️ Audio Speed: `{settings_data.audio_speed}x`
    • 🔊 Audio Volume: `{settings_data.audio_volume}%`
    """
    
    # Create settings keyboard
    keyboard = [
        [
            InlineKeyboardButton(f"🔄 Bulk: {settings_data.bulk_mode.upper()}", 
                               callback_data="settings_toggle_bulk"),
            InlineKeyboardButton(f"🖼️ Thumb: {'✅' if settings_data.thumbnail else '❌'}", 
                               callback_data="settings_toggle_thumb")
        ],
        [
            InlineKeyboardButton(f"📝 Rename: {'✅' if settings_data.rename_files else '❌'}", 
                               callback_data="settings_toggle_rename"),
            InlineKeyboardButton(f"⬆️ Upload: {settings_data.upload_mode.upper()}", 
                               callback_data="settings_cycle_upload")
        ],
        [
            InlineKeyboardButton(f"📊 Metadata: {'✅' if settings_data.video_metadata else '❌'}", 
                               callback_data="settings_toggle_metadata"),
            InlineKeyboardButton("🎵 Audio Settings", callback_data="settings_audio")
        ],
        [
            InlineKeyboardButton("🎵 MP3 Tags", callback_data="settings_mp3_tags"),
            InlineKeyboardButton("🔊 Audio Effects", callback_data="settings_effects")
        ],
        [
            InlineKeyboardButton("🔄 Reset Settings", callback_data="settings_reset"),
            InlineKeyboardButton("❌ Close", callback_data="settings_close")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        settings_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    # Get current settings
    settings_data = await DatabaseOperations.get_user_settings(user_id)
    
    if action == "settings_toggle_bulk":
        new_mode = "on" if settings_data.bulk_mode == "off" else "off"
        await DatabaseOperations.update_settings(user_id, bulk_mode=new_mode)
    
    elif action == "settings_toggle_thumb":
        await DatabaseOperations.update_settings(user_id, thumbnail=not settings_data.thumbnail)
    
    elif action == "settings_toggle_rename":
        await DatabaseOperations.update_settings(user_id, rename_files=not settings_data.rename_files)
    
    elif action == "settings_cycle_upload":
        modes = ["video", "audio", "document"]
        current_idx = modes.index(settings_data.upload_mode)
        next_mode = modes[(current_idx + 1) % len(modes)]
        await DatabaseOperations.update_settings(user_id, upload_mode=next_mode)
    
    elif action == "settings_toggle_metadata":
        await DatabaseOperations.update_settings(user_id, video_metadata=not settings_data.video_metadata)
    
    elif action == "settings_audio":
        await show_audio_settings(query, settings_data)
        return
    
    elif action == "settings_mp3_tags":
        await show_mp3_tags(query, settings_data)
        return
    
    elif action == "settings_effects":
        await show_audio_effects(query, settings_data)
        return
    
    elif action == "settings_reset":
        await DatabaseOperations.reset_settings(user_id)
        await query.edit_message_text("✅ Settings reset to defaults!")
        return
    
    elif action == "settings_close":
        await query.delete_message()
        return
    
    # Refresh settings display
    await settings(update, context)

async def show_audio_settings(query, settings_data):
    """Show audio settings panel"""
    keyboard = [
        [
            InlineKeyboardButton(f"Bitrate: {settings_data.audio_bitrate}", 
                               callback_data="audio_bitrate_menu"),
            InlineKeyboardButton(f"Sample: {settings_data.audio_sample_rate}Hz", 
                               callback_data="audio_sample_menu")
        ],
        [
            InlineKeyboardButton(f"Speed: {settings_data.audio_speed}x", 
                               callback_data="audio_speed_menu"),
            InlineKeyboardButton(f"Volume: {settings_data.audio_volume}%", 
                               callback_data="audio_volume_menu")
        ],
        [
            InlineKeyboardButton(f"Compress: {'ON' if settings_data.compress_audio else 'OFF'}", 
                               callback_data="audio_toggle_compress"),
            InlineKeyboardButton(f"Quality: {settings_data.compress_quality}/10", 
                               callback_data="audio_quality_menu")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
    🔊 *Audio Settings*
    
    Configure audio processing settings:
    • Bitrate: Audio quality (higher = better)
    • Sample Rate: Audio frequency
    • Speed: Playback speed
    • Volume: Audio loudness
    • Compression: Reduce file size
    • Quality: Compression level
    """
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_mp3_tags(query, settings_data):
    """Show MP3 tag editor"""
    keyboard = [
        [InlineKeyboardButton("Title", callback_data="mp3_title")],
        [InlineKeyboardButton("Artist", callback_data="mp3_artist")],
        [InlineKeyboardButton("Album", callback_data="mp3_album")],
        [InlineKeyboardButton("Year", callback_data="mp3_year")],
        [InlineKeyboardButton("Genre", callback_data="mp3_genre")],
        [InlineKeyboardButton("Cover Art", callback_data="mp3_cover")],
        [InlineKeyboardButton("Clear All", callback_data="mp3_clear")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    tags_text = "\n".join([f"• {k}: {v}" for k, v in settings_data.mp3_tags.items()])
    if not tags_text:
        tags_text = "No tags set"
    
    text = f"""
    🎵 *MP3 Tag Editor*
    
    Current Tags:
    {tags_text}
    
    Click to edit each tag.
    """
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_audio_effects(query, settings_data):
    """Show audio effects settings"""
    keyboard = [
        [InlineKeyboardButton("8D Audio", callback_data="effect_8d")],
        [InlineKeyboardButton("Reverb", callback_data="effect_reverb")],
        [InlineKeyboardButton("Equalizer", callback_data="effect_eq")],
        [InlineKeyboardButton("Bass Boost", callback_data="effect_bass")],
        [InlineKeyboardButton("Treble Boost", callback_data="effect_treble")],
        [InlineKeyboardButton("Normalize", callback_data="effect_normalize")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
    🎛️ *Audio Effects*
    
    Available effects:
    • 8D Audio: 3D audio experience
    • Reverb: Add echo/reverb
    • Equalizer: Adjust frequency bands
    • Bass Boost: Enhance low frequencies
    • Treble Boost: Enhance high frequencies
    • Normalize: Balance audio levels
    
    Click to configure each effect.
    """
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
