from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

class UserTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"

class BulkMode(str, Enum):
    ON = "on"
    OFF = "off"

class UploadMode(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"

class UserSettings(BaseModel):
    user_id: int
    tier: UserTier = UserTier.FREE
    bulk_mode: BulkMode = BulkMode.OFF
    thumbnail: bool = True
    rename_files: bool = False
    upload_mode: UploadMode = UploadMode.VIDEO
    video_metadata: bool = True
    mp3_tags: Dict[str, str] = Field(default_factory=dict)
    audio_bitrate: str = "192k"
    audio_sample_rate: str = "44100"
    audio_channels: int = 2
    audio_speed: float = 1.0
    audio_volume: int = 100
    compress_audio: bool = False
    compress_quality: int = 5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessingJob(BaseModel):
    job_id: str
    user_id: int
    file_id: str
    file_type: str
    action: str
    status: str  # pending, processing, completed, failed
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

class UserHistory(BaseModel):
    user_id: int
    action: str
    file_type: str
    file_size: int
    processing_time: float
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BulkOperation(BaseModel):
    operation_id: str
    user_id: int
    type: str
    files: List[str]
    status: str
    results: List[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)
