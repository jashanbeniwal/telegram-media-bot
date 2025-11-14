import os
import re
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from database import db
from utils.ffmpeg_processor import ffmpeg_processor
from utils.validators import validate_time_format, validate_credits

async def thumbnail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits. Please contact admin.")
        return
    
    job_id = await db.create_job('thumbnail_jobs', {
        'user_id': user_id,
        'command': 'thumbnail'
    })
    
    await update.message.reply_text("📸 Send me a video to extract thumbnail from")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'thumbnail'

async def trim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /trim start_time end_time\\nExample: /trim 00:00:10 00:00:30")
        return
    
    start_time, end_time = context.args
    if not validate_time_format(start_time) or not validate_time_format(end_time):
        await update.message.reply_text("❌ Invalid time format. Use HH:MM:SS")
        return
    
    job_id = await db.create_job('trim_jobs', {
        'user_id': user_id,
        'command': 'trim',
        'start_time': start_time,
        'end_time': end_time
    })
    
    await update.message.reply_text(f"✂️ Send me a video to trim from {start_time} to {end_time}")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'trim'
    context.user_data['start_time'] = start_time
    context.user_data['end_time'] = end_time

async def merge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    job_id = await db.create_job('merge_jobs', {
        'user_id': user_id,
        'command': 'merge'
    })
    
    await update.message.reply_text(
        "🔗 Send me multiple videos to merge (one by one).\\n"
        "When finished, send /done to start merging."
    )
    context.user_data['awaiting_videos'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'merge'
    context.user_data['videos_to_merge'] = []

async def split_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /split segment_time\\nExample: /split 00:05:00")
        return
    
    segment_time = context.args[0]
    if not validate_time_format(segment_time):
        await update.message.reply_text("❌ Invalid time format. Use HH:MM:SS")
        return
    
    job_id = await db.create_job('split_jobs', {
        'user_id': user_id,
        'command': 'split',
        'segment_time': segment_time
    })
    
    await update.message.reply_text(f"🪚 Send me a video to split into {segment_time} segments")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'split'
    context.user_data['segment_time'] = segment_time

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /screenshot time1,time2,...\\nExample: /screenshot 00:01:00,00:02:30")
        return
    
    timestamps = context.args[0].split(',')
    for timestamp in timestamps:
        if not validate_time_format(timestamp):
            await update.message.reply_text(f"❌ Invalid time format: {timestamp}. Use HH:MM:SS")
            return
    
    job_id = await db.create_job('screenshot_jobs', {
        'user_id': user_id,
        'command': 'screenshot',
        'timestamps': timestamps
    })
    
    await update.message.reply_text(f"📷 Send me a video to take screenshots at: {', '.join(timestamps)}")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'screenshot'
    context.user_data['timestamps'] = timestamps

async def optimize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    quality = context.args[0] if context.args else 'medium'
    if quality not in ['low', 'medium', 'high']:
        await update.message.reply_text("❌ Quality must be: low, medium, or high")
        return
    
    job_id = await db.create_job('optimize_jobs', {
        'user_id': user_id,
        'command': 'optimize',
        'quality': quality
    })
    
    await update.message.reply_text(f"⚡ Send me a video to optimize with {quality} quality")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'optimize'
    context.user_data['quality'] = quality

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = context.user_data
    
    if not user_data.get('awaiting_video') and not user_data.get('awaiting_videos'):
        return
    
    video = update.message.video or update.message.document
    
    if not video:
        await update.message.reply_text("❌ Please send a valid video file")
        return
    
    # Handle video merging (multiple videos)
    if user_data.get('awaiting_videos'):
        video_file = await context.bot.get_file(video.file_id)
        input_path = f"temp/inputs/{user_id}_{video.file_id}.mp4"
        os.makedirs("temp/inputs", exist_ok=True)
        await video_file.download_to_drive(input_path)
        
        user_data['videos_to_merge'].append(input_path)
        await update.message.reply_text(f"✅ Video added! Total: {len(user_data['videos_to_merge'])}. Send more or /done to merge.")
        return
    
    # Handle single video operations
    job_id = user_data.get('current_job')
    job_type = user_data.get('job_type')
    
    try:
        await update.message.reply_text("⏳ Processing your video...")
        
        # Download video
        video_file = await context.bot.get_file(video.file_id)
        input_path = f"temp/inputs/{user_id}_{video.file_id}.mp4"
        os.makedirs("temp/inputs", exist_ok=True)
        await video_file.download_to_drive(input_path)
        
        output_path = None
        
        # Process based on job type
        if job_type == 'thumbnail':
            output_path = await ffmpeg_processor.extract_thumbnail(input_path)
            await update.message.reply_photo(photo=open(output_path, 'rb'))
            await db.update_job_status('thumbnail_jobs', job_id, 'completed', 'Thumbnail extracted')
            
        elif job_type == 'trim':
            start_time = user_data.get('start_time')
            end_time = user_data.get('end_time')
            output_path = await ffmpeg_processor.trim_video(input_path, start_time, end_time)
            await update.message.reply_video(video=open(output_path, 'rb'))
            await db.update_job_status('trim_jobs', job_id, 'completed', 'Video trimmed')
            
        elif job_type == 'split':
            segment_time = user_data.get('segment_time')
            output_paths = await ffmpeg_processor.split_video(input_path, segment_time)
            for i, output_path in enumerate(output_paths):
                await update.message.reply_document(
                    document=open(output_path, 'rb'),
                    caption=f"Segment {i+1}"
                )
            await db.update_job_status('split_jobs', job_id, 'completed', f'Video split into {len(output_paths)} segments')
            
        elif job_type == 'screenshot':
            timestamps = user_data.get('timestamps')
            output_paths = await ffmpeg_processor.take_screenshots(input_path, timestamps)
            for i, output_path in enumerate(output_paths):
                await update.message.reply_photo(
                    photo=open(output_path, 'rb'),
                    caption=f"Screenshot at {timestamps[i]}"
                )
            await db.update_job_status('screenshot_jobs', job_id, 'completed', f'{len(output_paths)} screenshots taken')
            
        elif job_type == 'optimize':
            quality = user_data.get('quality')
            output_path = await ffmpeg_processor.optimize_video(input_path, quality)
            await update.message.reply_video(video=open(output_path, 'rb'))
            await db.update_job_status('optimize_jobs', job_id, 'completed', f'Video optimized with {quality} quality')
        
        # Deduct credit
        await db.update_user_credits(user_id, -1)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing video: {str(e)}")
        await db.update_job_status('thumbnail_jobs', job_id, 'failed', error=str(e))
    
    finally:
        # Cleanup
        if os.path.exists(input_path):
            os.remove(input_path)
        if output_path and os.path.exists(output_path):
            if isinstance(output_path, list):
                for path in output_path:
                    if os.path.exists(path):
                        os.remove(path)
            else:
                os.remove(output_path)
        
        user_data.clear()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == 'merge_done':
        if not context.user_data.get('videos_to_merge') or len(context.user_data['videos_to_merge']) < 2:
            await query.edit_message_text("❌ Need at least 2 videos to merge")
            return
        
        try:
            await query.edit_message_text("⏳ Merging videos...")
            output_path = await ffmpeg_processor.merge_videos(context.user_data['videos_to_merge'])
            
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=open(output_path, 'rb'),
                caption="Merged video"
            )
            
            await db.update_user_credits(user_id, -1)
            await db.update_job_status('merge_jobs', context.user_data.get('current_job'), 'completed', 'Videos merged')
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error merging videos: {str(e)}")
        
        finally:
            # Cleanup
            for video_path in context.user_data.get('videos_to_merge', []):
                if os.path.exists(video_path):
                    os.remove(video_path)
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            context.user_data.clear()
