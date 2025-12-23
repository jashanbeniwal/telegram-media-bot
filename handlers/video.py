import os
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from config import config
from database.operations import get_db_operations
from utils.premium import check_premium_status
from utils.progress import ProgressHandler
from utils.ffmpeg_utils import FFmpegHandler
from features.video_features import (
    VideoTrimmer, VideoMerger, VideoConverter, SubtitleHandler,
    AudioExtractor, VideoOptimizer, GIFConverter, VideoSplitter,
    ScreenshotGenerator, VideoSampler, ArchiveCreator, MetadataEditor
)

logger = logging.getLogger(__name__)

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video messages"""
    user_id = update.effective_user.id
    
    # Check premium status
    is_premium = await check_premium_status(user_id)
    
    # Get user settings
    db_ops = await get_db_operations()
    settings = await db_ops.get_user_settings(user_id)
    
    if not settings:
        await update.message.reply_text("❌ Failed to load settings. Please try again.")
        return
    
    # Get video file
    video = update.message.video or update.message.video_note
    if not video:
        await update.message.reply_text("❌ No video found in message.")
        return
    
    # Check file size limits
    can_process, error_msg = await db_ops.can_process_file(user_id, video.file_size)
    if not can_process:
        await update.message.reply_text(f"❌ {error_msg}")
        return
    
    # Store video info in context
    context.user_data['current_video'] = {
        'file_id': video.file_id,
        'file_size': video.file_size,
        'duration': video.duration,
        'width': getattr(video, 'width', 0),
        'height': getattr(video, 'height', 0),
        'file_name': getattr(video, 'file_name', f"video_{video.file_id}.mp4"),
        'mime_type': getattr(video, 'mime_type', 'video/mp4')
    }
    
    # Show processing options
    await show_video_options(update, context, is_premium)

async def show_video_options(update: Update, context: ContextTypes.DEFAULT_TYPE, is_premium: bool):
    """Show video processing options"""
    video_info = context.user_data.get('current_video', {})
    
    # Premium badge
    premium_text = "⭐ PREMIUM" if is_premium else "🆓 FREE"
    
    # Create keyboard with all video features
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Thumbnail Extractor", callback_data="video_thumbnail"),
            InlineKeyboardButton("📝 Caption Editor", callback_data="video_caption"),
        ],
        [
            InlineKeyboardButton("📊 Metadata Editor", callback_data="video_metadata"),
            InlineKeyboardButton("📤 Media Forwarder", callback_data="video_forward"),
        ],
        [
            InlineKeyboardButton("🎵 Stream Remover/Extractor", callback_data="video_stream"),
            InlineKeyboardButton("✂️ Video Trimmer", callback_data="video_trim"),
        ],
        [
            InlineKeyboardButton("🔀 Video Splitter", callback_data="video_split"),
            InlineKeyboardButton("🔗 Video Merger", callback_data="video_merge"),
        ],
        [
            InlineKeyboardButton("🔇 Remove Audio", callback_data="video_mute"),
            InlineKeyboardButton("🎵 Merge Video & Audio", callback_data="video_merge_audio"),
        ],
        [
            InlineKeyboardButton("🎵 Audio Converter", callback_data="video_audio_convert"),
            InlineKeyboardButton("🎬 Generate Sample", callback_data="video_sample"),
        ],
        [
            InlineKeyboardButton("🎵 Video to Audio", callback_data="video_to_audio"),
            InlineKeyboardButton("⚡ Video Optimizer", callback_data="video_optimize"),
        ],
        [
            InlineKeyboardButton("📝 Subtitle Merger", callback_data="video_subtitle"),
            InlineKeyboardButton("🔄 Video Converter", callback_data="video_convert"),
        ],
        [
            InlineKeyboardButton("📝 Video Renamer", callback_data="video_rename"),
            InlineKeyboardButton("ℹ️ Media Information", callback_data="video_info"),
        ],
        [
            InlineKeyboardButton("🗜️ Create Archive", callback_data="video_archive"),
            InlineKeyboardButton("❌ Cancel", callback_data="video_cancel"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
    🎥 **Video Detected!**
    
    📊 File Info:
    • Name: `{video_info.get('file_name', 'Unknown')}`
    • Size: {video_info.get('file_size', 0) // (1024*1024)} MB
    • Duration: {video_info.get('duration', 0)} seconds
    • Resolution: {video_info.get('width', 0)}x{video_info.get('height', 0)}
    
    👤 User: {update.effective_user.first_name}
    📊 Status: {premium_text}
    
    Select an action below:
    """
    
    if update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video callback queries"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = update.effective_user.id
    
    # Get video info from context
    video_info = context.user_data.get('current_video', {})
    if not video_info:
        await query.edit_message_text("❌ No video found. Please send a video first.")
        return
    
    # Handle different actions
    if action == "video_thumbnail":
        await extract_thumbnail(query, video_info)
        
    elif action == "video_trim":
        await trim_video(query, video_info)
        
    elif action == "video_split":
        await split_video(query, video_info)
        
    elif action == "video_merge":
        await merge_videos(query, user_id)
        
    elif action == "video_mute":
        await mute_audio(query, video_info)
        
    elif action == "video_stream":
        await stream_operations(query, video_info)
        
    elif action == "video_convert":
        await convert_video(query, video_info)
        
    elif action == "video_to_audio":
        await video_to_audio(query, video_info)
        
    elif action == "video_optimize":
        await optimize_video(query, video_info)
        
    elif action == "video_sample":
        await generate_sample(query, video_info)
        
    elif action == "video_subtitle":
        await merge_subtitle(query, video_info)
        
    elif action == "video_archive":
        await create_archive(query, video_info)
        
    elif action == "video_info":
        await show_media_info(query, video_info)
        
    elif action == "video_cancel":
        await query.delete_message()
        if 'current_video' in context.user_data:
            del context.user_data['current_video']

async def extract_thumbnail(query, video_info):
    """Extract thumbnail from video"""
    await query.edit_message_text("🖼️ Extracting thumbnail...")
    
    try:
        # Download video
        file_path = await download_file(query.bot, video_info['file_id'])
        
        # Use FFmpeg to extract thumbnail
        ffmpeg = FFmpegHandler()
        thumbnail_path = await ffmpeg.extract_thumbnail(file_path)
        
        # Send thumbnail
        with open(thumbnail_path, 'rb') as thumb:
            await query.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=thumb,
                caption="✅ Thumbnail extracted successfully!"
            )
        
        # Cleanup
        os.remove(file_path)
        os.remove(thumbnail_path)
        
    except Exception as e:
        logger.error(f"Error extracting thumbnail: {e}")
        await query.edit_message_text(f"❌ Error extracting thumbnail: {str(e)}")

async def trim_video(query, video_info):
    """Trim video with time selection"""
    await query.edit_message_text(
        "✂️ **Video Trimmer**\n\n"
        "Please send start and end times in format:\n"
        "`start_time end_time`\n\n"
        "Example: `00:10 01:30`\n"
        "Or send `auto` for automatic trimming."
    )
    
    # Store state for next message
    query.message.chat_data['awaiting_trim_times'] = True

async def split_video(query, video_info):
    """Split video into parts"""
    await query.edit_message_text(
        "🔀 **Video Splitter**\n\n"
        "Choose split method:\n\n"
        "1. By duration (e.g., '60' for 60-second parts)\n"
        "2. By number of parts (e.g., '3' for 3 equal parts)\n"
        "3. By timestamps (e.g., '00:30,01:00,01:30')\n\n"
        "Send your choice:"
    )
    
    query.message.chat_data['awaiting_split_method'] = True

async def mute_audio(query, video_info):
    """Remove audio from video"""
    await query.edit_message_text("🔇 Removing audio from video...")
    
    try:
        # Download video
        file_path = await download_file(query.bot, video_info['file_id'])
        
        # Use FFmpeg to remove audio
        ffmpeg = FFmpegHandler()
        output_path = await ffmpeg.remove_audio(file_path)
        
        # Send muted video
        with open(output_path, 'rb') as video_file:
            await query.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption="✅ Audio removed successfully!"
            )
        
        # Cleanup
        os.remove(file_path)
        os.remove(output_path)
        
    except Exception as e:
        logger.error(f"Error removing audio: {e}")
        await query.edit_message_text(f"❌ Error removing audio: {str(e)}")

async def convert_video(query, video_info):
    """Convert video to different format"""
    keyboard = [
        [
            InlineKeyboardButton("MP4", callback_data="convert_mp4"),
            InlineKeyboardButton("MKV", callback_data="convert_mkv"),
            InlineKeyboardButton("AVI", callback_data="convert_avi"),
        ],
        [
            InlineKeyboardButton("MOV", callback_data="convert_mov"),
            InlineKeyboardButton("WEBM", callback_data="convert_webm"),
            InlineKeyboardButton("M4V", callback_data="convert_m4v"),
        ],
        [
            InlineKeyboardButton("GIF", callback_data="convert_gif"),
            InlineKeyboardButton("🔙 Back", callback_data="video_back"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 **Video Converter**\n\n"
        "Select output format:",
        reply_markup=reply_markup
    )

async def video_to_audio(query, video_info):
    """Convert video to audio"""
    keyboard = [
        [
            InlineKeyboardButton("MP3", callback_data="audio_mp3"),
            InlineKeyboardButton("WAV", callback_data="audio_wav"),
            InlineKeyboardButton("AAC", callback_data="audio_aac"),
        ],
        [
            InlineKeyboardButton("FLAC", callback_data="audio_flac"),
            InlineKeyboardButton("M4A", callback_data="audio_m4a"),
            InlineKeyboardButton("OPUS", callback_data="audio_opus"),
        ],
        [
            InlineKeyboardButton("OGG", callback_data="audio_ogg"),
            InlineKeyboardButton("WMA", callback_data="audio_wma"),
            InlineKeyboardButton("AC3", callback_data="audio_ac3"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="video_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎵 **Video to Audio Converter**\n\n"
        "Select audio format:",
        reply_markup=reply_markup
    )

async def download_file(bot, file_id, file_name=None):
    """Download file from Telegram"""
    file = await bot.get_file(file_id)
    
    if not file_name:
        file_name = f"temp_{file_id}"
    
    file_path = os.path.join(config.TEMP_DIR, file_name)
    
    # Create temp directory if not exists
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    
    await file.download_to_drive(file_path)
    
    return file_path

# More video feature implementations would follow similar patterns...
