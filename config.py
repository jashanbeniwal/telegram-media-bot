import os
from typing import Dict, List, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Bot Configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "").strip("@")
    
    # MongoDB Configuration
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "telegram_bot")
    
    # Premium Settings
    PREMIUM_USER_IDS: List[int] = list(map(int, os.getenv("PREMIUM_USER_IDS", "").split(","))) if os.getenv("PREMIUM_USER_IDS") else []
    FREE_USER_WAIT_TIME: int = int(os.getenv("FREE_USER_WAIT_TIME", 1800))  # 30 minutes in seconds
    MAX_FILE_SIZE_FREE: int = int(os.getenv("MAX_FILE_SIZE_FREE", 500 * 1024 * 1024))  # 500MB
    MAX_FILE_SIZE_PREMIUM: int = int(os.getenv("MAX_FILE_SIZE_PREMIUM", 2 * 1024 * 1024 * 1024))  # 2GB
    
    # Processing Settings
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", 5))
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")
    
    # FFmpeg Settings
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", "ffprobe")
    
    # Audio Settings Defaults
    DEFAULT_AUDIO_BITRATE: str = "192k"
    DEFAULT_AUDIO_CODEC: str = "libmp3lame"
    AUDIO_QUALITIES: Dict[str, Dict[str, Any]] = {
        "low": {"bitrate": "128k", "sample_rate": "44100"},
        "medium": {"bitrate": "192k", "sample_rate": "44100"},
        "high": {"bitrate": "320k", "sample_rate": "48000"},
        "lossless": {"bitrate": "1411k", "sample_rate": "44100"}
    }
    
    # Video Settings Defaults
    VIDEO_QUALITIES: Dict[str, Dict[str, Any]] = {
        "360p": {"resolution": "640x360", "bitrate": "800k"},
        "480p": {"resolution": "854x480", "bitrate": "1200k"},
        "720p": {"resolution": "1280x720", "bitrate": "2500k"},
        "1080p": {"resolution": "1920x1080", "bitrate": "5000k"}
    }
    
    # Supported Formats
    SUPPORTED_AUDIO_FORMATS: List[str] = ["mp3", "wav", "aac", "flac", "m4a", "opus", "ogg", "wma", "ac3"]
    SUPPORTED_VIDEO_FORMATS: List[str] = ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"]
    SUPPORTED_DOCUMENT_FORMATS: List[str] = ["txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "zip", "rar", "7z", "json", "srt", "vtt", "ass", "sbv"]
    
    # Server Configuration (for Koyeb)
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    PORT: int = int(os.getenv("PORT", 8080))
    HOST: str = os.getenv("HOST", "0.0.0.0")

config = Config()
