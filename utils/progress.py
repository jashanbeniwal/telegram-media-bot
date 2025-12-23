import asyncio
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes

class ProgressHandler:
    def __init__(self):
        self.progress_bars = {}
    
    async def create_progress_bar(self, chat_id: int, total: int, description: str = "Processing"):
        """Create a progress bar message"""
        from telegram import Bot
        from config import config
        
        bot = Bot(config.BOT_TOKEN)
        
        message = await bot.send_message(
            chat_id=chat_id,
            text=f"{description}\n{self._get_bar(0)} 0%"
        )
        
        self.progress_bars[chat_id] = {
            'message_id': message.message_id,
            'total': total,
            'current': 0,
            'description': description
        }
        
        return message.message_id
    
    def _get_bar(self, percentage: int) -> str:
        """Get progress bar string"""
        bar_length = 20
        filled = int(bar_length * percentage / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        return f"[{bar}]"
    
    async def update_progress(self, chat_id: int, current: int):
        """Update progress bar"""
        if chat_id not in self.progress_bars:
            return
        
        data = self.progress_bars[chat_id]
        total = data['total']
        percentage = int((current / total) * 100)
        
        if percentage > 100:
            percentage = 100
        
        # Only update every 5% to avoid spam
        if percentage % 5 != 0 and percentage != 100:
            return
        
        from telegram import Bot
        from config import config
        
        bot = Bot(config.BOT_TOKEN)
        
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=data['message_id'],
                text=f"{data['description']}\n{self._get_bar(percentage)} {percentage}%"
            )
        except:
            pass
        
        if percentage == 100:
            del self.progress_bars[chat_id]
    
    async def download_with_progress(self, bot, file_id: str, file_path: str, 
                                   chat_id: int, description: str = "Downloading"):
        """Download file with progress"""
        file = await bot.get_file(file_id)
        file_size = file.file_size
        
        # Create progress bar
        await self.create_progress_bar(chat_id, file_size, description)
        
        # Download in chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        downloaded = 0
        
        with open(file_path, 'wb') as f:
            async for chunk in file.download_as_bytearray():
                f.write(chunk)
                downloaded += len(chunk)
                await self.update_progress(chat_id, downloaded)
        
        return file_path
    
    async def upload_with_progress(self, bot, chat_id: int, file_path: str, 
                                 caption: str = "", file_type: str = "document"):
        """Upload file with progress"""
        import os
        
        file_size = os.path.getsize(file_path)
        await self.create_progress_bar(chat_id, file_size, "Uploading")
        
        # Upload file
        with open(file_path, 'rb') as f:
            if file_type == "video":
                await bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=caption,
                    supports_streaming=True
                )
            elif file_type == "audio":
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=f,
                    caption=caption
                )
            else:
                await bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    caption=caption
                )
        
        # Remove progress bar
        if chat_id in self.progress_bars:
            data = self.progress_bars[chat_id]
            await bot.delete_message(chat_id=chat_id, message_id=data['message_id'])
            del self.progress_bars[chat_id]

progress = ProgressHandler()
