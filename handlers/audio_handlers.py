import os
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils.ffmpeg_processor import ffmpeg_processor
from utils.validators import validate_credits

async def extract_audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    format = context.args[0] if context.args else 'mp3'
    
    job_id = await db.create_job('audio_jobs', {
        'user_id': user_id,
        'command': 'extract_audio',
        'format': format
    })
    
    await update.message.reply_text(f"🎵 Send me a video to extract audio as {format.upper()}")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'extract_audio'
    context.user_data['format'] = format

async def remove_audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    job_id = await db.create_job('audio_jobs', {
        'user_id': user_id,
        'command': 'remove_audio'
    })
    
    await update.message.reply_text("🔇 Send me a video to remove audio from")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'remove_audio'

async def convert_audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /convert_audio format\\nFormats: mp3, wav, aac, ogg")
        return
    
    format = context.args[0].lower()
    if format not in ['mp3', 'wav', 'aac', 'ogg', 'flac']:
        await update.message.reply_text("❌ Supported formats: mp3, wav, aac, ogg, flac")
        return
    
    job_id = await db.create_job('audio_jobs', {
        'user_id': user_id,
        'command': 'convert_audio',
        'format': format
    })
    
    await update.message.reply_text(f"🔄 Send me an audio file to convert to {format.upper()}")
    context.user_data['awaiting_audio'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'convert_audio'
    context.user_data['format'] = format

async def video_to_audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await validate_credits(user_id):
        await update.message.reply_text("❌ Insufficient credits.")
        return
    
    format = context.args[0] if context.args else 'mp3'
    
    job_id = await db.create_job('audio_jobs', {
        'user_id': user_id,
        'command': 'video_to_audio',
        'format': format
    })
    
    await update.message.reply_text(f"🎬 Send me a video to convert to {format.upper()} audio")
    context.user_data['awaiting_video'] = True
    context.user_data['current_job'] = job_id
    context.user_data['job_type'] = 'video_to_audio'
    context.user_data['format'] = format

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = context.user_data
    
    if not user_data.get('awaiting_audio'):
        return
    
    audio = update.message.audio or update.message.document
    
    if not audio:
        await update.message.reply_text("❌ Please send a valid audio file")
        return
    
    job_id = user_data.get('current_job')
    job_type = user_data.get('job_type')
    
    try:
        await update.message.reply_text("⏳ Processing your audio...")
        
        # Download audio
        audio_file = await context.bot.get_file(audio.file_id)
        input_path = f"temp/inputs/{user_id}_{audio.file_id}"
        
        # Get file extension
        if update.message.audio:
            ext = audio.mime_type.split('/')[-1] if audio.mime_type else 'mp3'
        else:
            ext = audio.file_name.split('.')[-1] if audio.file_name else 'mp3'
        
        input_path += f".{ext}"
        os.makedirs("temp/inputs", exist_ok=True)
        await audio_file.download_to_drive(input_path)
        
        output_path = None
        
        if job_type == 'convert_audio':
            format = user_data.get('format')
            output_path = await ffmpeg_processor.convert_audio(input_path, format)
            await update.message.reply_audio(audio=open(output_path, 'rb'))
            await db.update_job_status('audio_jobs', job_id, 'completed', f'Audio converted to {format}')
        
        # Deduct credit
        await db.update_user_credits(user_id, -1)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing audio: {str(e)}")
        await db.update_job_status('audio_jobs', job_id, 'failed', error=str(e))
    
    finally:
        # Cleanup
        if os.path.exists(input_path):
            os.remove(input_path)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
        
        user_data.clear()
