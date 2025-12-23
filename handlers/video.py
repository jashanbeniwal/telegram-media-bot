import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.operations import DatabaseOperations
from utils.premium import is_premium_user, check_wait_time
from utils.ffmpeg_utils import FFmpegHandler
from utils.progress import ProgressHandler

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming video"""
    user_id = update.effective_user.id
    
    # Check if user can process
    video = update.message.video or update.message.video_note
    file_size = video.file_size
    
    can_process, message = await DatabaseOperations.can_process(user_id, file_size)
    if not can_process:
        await update.message.reply_text(f"❌ {message}")
        return
    
    # Store video info
    context.user_data['current_video'] = {
        'file_id': video.file_id,
        'file_size': file_size,
        'duration': video.duration,
        'width': getattr(video, 'width', 0),
        'height': getattr(video, 'height', 0),
        'file_name': getattr(video, 'file_name', f"video_{video.file_id}.mp4")
    }
    
    # Show video options
    await show_video_options(update, context)

async def show_video_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show video processing options"""
    video_info = context.user_data.get('current_video', {})
    user_id = update.effective_user.id
    premium = await is_premium_user(user_id)
    
    # Create options keyboard
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Thumbnail", callback_data="video_thumbnail"),
            InlineKeyboardButton("📝 Caption", callback_data="video_caption")
        ],
        [
            InlineKeyboardButton("📊 Metadata", callback_data="video_metadata"),
            InlineKeyboardButton("📤 Forward", callback_data="video_forward")
        ],
        [
            InlineKeyboardButton("🎵 Extract Audio", callback_data="video_extract_audio"),
            InlineKeyboardButton("✂️ Trim", callback_data="video_trim")
        ],
        [
            InlineKeyboardButton("🔀 Split", callback_data="video_split"),
            InlineKeyboardButton("🔗 Merge", callback_data="video_merge")
        ],
        [
            InlineKeyboardButton("🔇 Mute", callback_data="video_mute"),
            InlineKeyboardButton("🎵 Merge Audio", callback_data="video_merge_audio")
        ],
        [
            InlineKeyboardButton("🔄 Convert", callback_data="video_convert"),
            InlineKeyboardButton("🎬 Sample", callback_data="video_sample")
        ],
        [
            InlineKeyboardButton("🎵 To Audio", callback_data="video_to_audio"),
            InlineKeyboardButton("⚡ Optimize", callback_data="video_optimize")
        ],
        [
            InlineKeyboardButton("📝 Subtitle", callback_data="video_subtitle"),
            InlineKeyboardButton("🔄 Converter", callback_data="video_converter")
        ],
        [
            InlineKeyboardButton("📝 Rename", callback_data="video_rename"),
            InlineKeyboardButton("ℹ️ Info", callback_data="video_info")
        ],
        [
            InlineKeyboardButton("🗜️ Archive", callback_data="video_archive"),
            InlineKeyboardButton("❌ Cancel", callback_data="video_cancel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
    🎥 *Video Detected*
    
    📊 *File Info*:
    • Name: `{video_info.get('file_name', 'Unknown')}`
    • Size: {video_info.get('file_size', 0) // (1024*1024)} MB
    • Duration: {video_info.get('duration', 0)}s
    • Resolution: {video_info.get('width', 0)}x{video_info.get('height', 0)}
    
    👤 *User*: {update.effective_user.first_name}
    📊 *Status*: {'⭐ PREMIUM' if premium else '🆓 FREE'}
    
    Select an action:
    """
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    video_info = context.user_data.get('current_video', {})
    
    if not video_info:
        await query.edit_message_text("❌ No video found. Send a video first.")
        return
    
    if action == "video_thumbnail":
        await extract_thumbnail(query, video_info)
    
    elif action == "video_extract_audio":
        await extract_audio(query, video_info)
    
    elif action == "video_trim":
        await trim_video(query, video_info)
    
    elif action == "video_mute":
        await mute_video(query, video_info)
    
    elif action == "video_to_audio":
        await convert_to_audio(query, video_info)
    
    elif action == "video_convert":
        await show_conversion_options(query)
    
    elif action == "video_info":
        await show_video_info(query, video_info)
    
    elif action == "video_cancel":
        await query.delete_message()
        if 'current_video' in context.user_data:
            del context.user_data['current_video']

async def extract_thumbnail(query, video_info):
    """Extract thumbnail from video"""
    await query.edit_message_text("🖼️ Extracting thumbnail...")
    
    try:
        # Download video
        file_path = await download_video(query.bot, video_info['file_id'])
        
        # Extract thumbnail
        ffmpeg = FFmpegHandler()
        thumbnail_path = await ffmpeg.extract_thumbnail(file_path)
        
        # Send thumbnail
        with open(thumbnail_path, 'rb') as thumb:
            await query.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=thumb,
                caption="✅ Thumbnail extracted!"
            )
        
        # Cleanup
        os.remove(file_path)
        os.remove(thumbnail_path)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def extract_audio(query, video_info):
    """Extract audio from video"""
    await query.edit_message_text("🎵 Extracting audio...")
    
    try:
        file_path = await download_video(query.bot, video_info['file_id'])
        
        ffmpeg = FFmpegHandler()
        audio_path = await ffmpeg.extract_audio(file_path)
        
        with open(audio_path, 'rb') as audio:
            await query.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio,
                caption="✅ Audio extracted!"
            )
        
        os.remove(file_path)
        os.remove(audio_path)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def trim_video(query, video_info):
    """Trim video"""
    await query.edit_message_text(
        "✂️ *Video Trimmer*\n\n"
        "Send start and end times:\n"
        "Format: `HH:MM:SS` or `MM:SS`\n\n"
        "Example: `00:10 01:30`\n"
        "Or send `auto` for automatic trimming."
    )
    
    # Set state for next message
    context = query.message
    context.chat_data['awaiting_trim'] = True

async def mute_video(query, video_info):
    """Remove audio from video"""
    await query.edit_message_text("🔇 Removing audio...")
    
    try:
        file_path = await download_video(query.bot, video_info['file_id'])
        
        ffmpeg = FFmpegHandler()
        muted_path = await ffmpeg.remove_audio(file_path)
        
        with open(muted_path, 'rb') as video:
            await query.bot.send_video(
                chat_id=query.message.chat_id,
                video=video,
                caption="✅ Audio removed!"
            )
        
        os.remove(file_path)
        os.remove(muted_path)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def convert_to_audio(query, video_info):
    """Convert video to audio"""
    keyboard = [
        [InlineKeyboardButton("MP3", callback_data="audio_mp3")],
        [InlineKeyboardButton("WAV", callback_data="audio_wav")],
        [InlineKeyboardButton("FLAC", callback_data="audio_flac")],
        [InlineKeyboardButton("AAC", callback_data="audio_aac")],
        [InlineKeyboardButton("M4A", callback_data="audio_m4a")],
        [InlineKeyboardButton("Back", callback_data="video_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎵 Convert to audio format:",
        reply_markup=reply_markup
    )

async def show_conversion_options(query):
    """Show video conversion options"""
    keyboard = [
        [InlineKeyboardButton("MP4", callback_data="convert_mp4")],
        [InlineKeyboardButton("MKV", callback_data="convert_mkv")],
        [InlineKeyboardButton("AVI", callback_data="convert_avi")],
        [InlineKeyboardButton("MOV", callback_data="convert_mov")],
        [InlineKeyboardButton("WEBM", callback_data="convert_webm")],
        [InlineKeyboardButton("GIF", callback_data="convert_gif")],
        [InlineKeyboardButton("Back", callback_data="video_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 Convert to format:",
        reply_markup=reply_markup
    )

async def show_video_info(query, video_info):
    """Show video information"""
    try:
        file_path = await download_video(query.bot, video_info['file_id'])
        
        ffmpeg = FFmpegHandler()
        info = await ffmpeg.get_media_info(file_path)
        
        text = f"""
        📊 *Media Information*
        
        *General*:
        • Format: {info.get('format', {}).get('format_name', 'N/A')}
        • Duration: {float(info.get('format', {}).get('duration', 0)):.2f}s
        • Size: {int(info.get('format', {}).get('size', 0)) // (1024*1024)} MB
        • Bitrate: {int(info.get('format', {}).get('bit_rate', 0)) // 1000} kbps
        
        *Video Stream*:
        • Codec: {next((s.get('codec_name') for s in info.get('streams', []) if s.get('codec_type') == 'video'), 'N/A')}
        • Resolution: {next((f"{s.get('width')}x{s.get('height')}" for s in info.get('streams', []) if s.get('codec_type') == 'video'), 'N/A')}
        • FPS: {next((eval(s.get('avg_frame_rate', '0')) for s in info.get('streams', []) if s.get('codec_type') == 'video'), 0):.2f}
        
        *Audio Stream*:
        • Codec: {next((s.get('codec_name') for s in info.get('streams', []) if s.get('codec_type') == 'audio'), 'N/A')}
        • Channels: {next((s.get('channels') for s in info.get('streams', []) if s.get('codec_type') == 'audio'), 'N/A')}
        • Sample Rate: {next((s.get('sample_rate') for s in info.get('streams', []) if s.get('codec_type') == 'audio'), 'N/A')} Hz
        """
        
        await query.edit_message_text(text, parse_mode="Markdown")
        
        os.remove(file_path)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def download_video(bot, file_id):
    """Download video from Telegram"""
    file = await bot.get_file(file_id)
    file_path = os.path.join("temp", f"video_{file_id}.mp4")
    await file.download_to_drive(file_path)
    return file_path
