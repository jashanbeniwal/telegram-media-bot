from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from pydantic import BaseModel, Field
from enum import Enum

class UserTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"

class BulkMode(str, Enum):
    ON = "on"
    OFF = "off"

class UploadMode(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"

class AudioFormat(str, Enum):
    MP3 = "mp3"
    WAV = "wav"
    AAC = "aac"
    FLAC = "flac"
    M4A = "m4a"
    OPUS = "opus"
    OGG = "ogg"
    WMA = "wma"
    AC3 = "ac3"

class VideoFormat(str, Enum):
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    MOV = "mov"
    WEBM = "webm"
    M4V = "m4v"

class SubtitleFormat(str, Enum):
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    SBV = "sbv"

class ArchiveFormat(str, Enum):
    ZIP = "zip"
    RAR = "rar"
    SEVENZ = "7z"

class UserSettings(BaseModel):
    user_id: int
    tier: UserTier = UserTier.FREE
    bulk_mode: BulkMode = BulkMode.OFF
    thumbnail_enabled: bool = True
    rename_files: bool = False
    upload_mode: UploadMode = UploadMode.VIDEO
    video_metadata: bool = True
    mp3_tags: Dict[str, str] = Field(default_factory=dict)
    audio_settings: Dict[str, Any] = Field(default_factory=lambda: {
        "bitrate": "192k",
        "sample_rate": "44100",
        "channels": 2
    })
    audio_speed: float = 1.0
    audio_volume: int = 100
    compress_audio: bool = False
    compress_quality: int = 5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }

class ProcessingJob(BaseModel):
    job_id: str
    user_id: int
    file_id: str
    file_type: str
    original_filename: str
    status: str  # pending, processing, completed, failed
    action: str
    settings_used: Dict[str, Any]
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    processing_time: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }

class UserHistory(BaseModel):
    user_id: int
    action: str
    file_type: str
    original_filename: str
    processed_filename: Optional[str] = None
    file_size: int
    processing_time: float
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }

class BulkOperation(BaseModel):
    operation_id: str
    user_id: int
    operation_type: str
    file_ids: List[str]
    settings: Dict[str, Any]
    status: str
    results: List[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: str
        }
