from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId

from config import config
from database.models import (
    UserSettings, ProcessingJob, UserHistory, BulkOperation,
    UserTier, BulkMode, UploadMode
)

class DatabaseOperations:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.users = db.users
        self.jobs = db.processing_jobs
        self.history = db.user_history
        self.bulk_ops = db.bulk_operations
        self.settings = db.user_settings
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user from database"""
        return await self.users.find_one({"user_id": user_id})
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
        """Create new user in database"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "tier": UserTier.PREMIUM if user_id in config.PREMIUM_USER_IDS else UserTier.FREE,
            "joined_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "total_files_processed": 0,
            "total_processing_time": 0
        }
        
        result = await self.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        
        # Initialize default settings
        await self.init_user_settings(user_id)
        
        return user_data
    
    async def init_user_settings(self, user_id: int) -> UserSettings:
        """Initialize default settings for user"""
        settings = UserSettings(
            user_id=user_id,
            tier=UserTier.PREMIUM if user_id in config.PREMIUM_USER_IDS else UserTier.FREE
        )
        
        await self.settings.update_one(
            {"user_id": user_id},
            {"$set": settings.dict()},
            upsert=True
        )
        
        return settings
    
    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Get user settings"""
        data = await self.settings.find_one({"user_id": user_id})
        if data:
            return UserSettings(**data)
        return None
    
    async def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """Update user settings"""
        kwargs["updated_at"] = datetime.utcnow()
        
        result = await self.settings.update_one(
            {"user_id": user_id},
            {"$set": kwargs}
        )
        
        return result.modified_count > 0
    
    async def reset_user_settings(self, user_id: int) -> bool:
        """Reset user settings to default"""
        settings = UserSettings(user_id=user_id)
        
        result = await self.settings.update_one(
            {"user_id": user_id},
            {"$set": settings.dict()}
        )
        
        return result.modified_count > 0
    
    async def create_processing_job(self, **kwargs) -> str:
        """Create a new processing job"""
        job = ProcessingJob(**kwargs)
        
        result = await self.jobs.insert_one(job.dict())
        return str(result.inserted_id)
    
    async def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        """Update job status"""
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        
        if status == "completed":
            update_data["end_time"] = datetime.utcnow()
            if "processing_time" in kwargs:
                update_data["processing_time"] = kwargs["processing_time"]
        
        if "error_message" in kwargs:
            update_data["error_message"] = kwargs["error_message"]
        
        if "output_path" in kwargs:
            update_data["output_path"] = kwargs["output_path"]
        
        result = await self.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    async def add_to_history(self, user_id: int, **kwargs) -> str:
        """Add entry to user history"""
        history = UserHistory(user_id=user_id, **kwargs)
        
        result = await self.history.insert_one(history.dict())
        
        # Update user stats
        await self.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "total_files_processed": 1,
                    "total_processing_time": history.processing_time or 0
                },
                "$set": {"last_active": datetime.utcnow()}
            }
        )
        
        return str(result.inserted_id)
    
    async def get_user_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's processing history"""
        cursor = self.history.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def create_bulk_operation(self, user_id: int, operation_type: str, file_ids: List[str], settings: Dict[str, Any]) -> str:
        """Create a new bulk operation"""
        operation = BulkOperation(
            operation_id=ObjectId(),
            user_id=user_id,
            operation_type=operation_type,
            file_ids=file_ids,
            settings=settings,
            status="pending",
            results=[]
        )
        
        result = await self.bulk_ops.insert_one(operation.dict())
        return str(result.inserted_id)
    
    async def update_bulk_operation(self, operation_id: str, **kwargs) -> bool:
        """Update bulk operation"""
        if "status" in kwargs and kwargs["status"] == "completed":
            kwargs["completed_at"] = datetime.utcnow()
        
        result = await self.bulk_ops.update_one(
            {"_id": ObjectId(operation_id)},
            {"$set": kwargs}
        )
        
        return result.modified_count > 0
    
    async def get_active_jobs_count(self, user_id: int) -> int:
        """Get count of active jobs for user"""
        return await self.jobs.count_documents({
            "user_id": user_id,
            "status": {"$in": ["pending", "processing"]}
        })
    
    async def can_process_file(self, user_id: int, file_size: int) -> tuple[bool, str]:
        """Check if user can process a file"""
        user = await self.get_user(user_id)
        
        if not user:
            return False, "User not found"
        
        # Check file size limit
        max_size = config.MAX_FILE_SIZE_PREMIUM if user["tier"] == UserTier.PREMIUM else config.MAX_FILE_SIZE_FREE
        if file_size > max_size:
            return False, f"File size exceeds limit. Max: {max_size // (1024*1024)}MB"
        
        # Check concurrent jobs limit
        active_jobs = await self.get_active_jobs_count(user_id)
        if active_jobs >= config.MAX_CONCURRENT_JOBS:
            return False, "Maximum concurrent jobs reached. Please wait."
        
        # Check wait time for free users
        if user["tier"] == UserTier.FREE:
            last_job = await self.jobs.find_one(
                {"user_id": user_id, "status": "completed"},
                sort=[("end_time", -1)]
            )
            
            if last_job and last_job.get("end_time"):
                time_since_last = datetime.utcnow() - last_job["end_time"]
                if time_since_last.total_seconds() < config.FREE_USER_WAIT_TIME:
                    wait_time = config.FREE_USER_WAIT_TIME - time_since_last.total_seconds()
                    return False, f"Free users must wait {int(wait_time/60)} minutes between files"
        
        return True, ""

# Singleton instance
_db_operations = None

async def get_db_operations() -> DatabaseOperations:
    """Get database operations instance"""
    global _db_operations
    if _db_operations is None:
        from database.connection import get_database
        db = await get_database()
        _db_operations = DatabaseOperations(db)
    return _db_operations
