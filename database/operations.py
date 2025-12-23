from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
from database.connection import get_database
from database.models import UserSettings, ProcessingJob, UserHistory, BulkOperation

class DatabaseOperations:
    @staticmethod
    async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
        db = await get_database()
        return await db.users.find_one({"user_id": user_id})
    
    @staticmethod
    async def create_user(user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
        db = await get_database()
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "tier": "premium" if user_id in [123456789] else "free",  # Default premium IDs
            "joined": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "total_files": 0,
            "total_size": 0
        }
        
        result = await db.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        
        # Initialize settings
        await DatabaseOperations.init_user_settings(user_id)
        
        return user_data
    
    @staticmethod
    async def init_user_settings(user_id: int):
        db = await get_database()
        settings = UserSettings(user_id=user_id)
        await db.settings.update_one(
            {"user_id": user_id},
            {"$set": settings.dict()},
            upsert=True
        )
    
    @staticmethod
    async def get_user_settings(user_id: int) -> Optional[UserSettings]:
        db = await get_database()
        data = await db.settings.find_one({"user_id": user_id})
        if data:
            return UserSettings(**data)
        return None
    
    @staticmethod
    async def update_settings(user_id: int, **kwargs):
        db = await get_database()
        kwargs["updated_at"] = datetime.utcnow()
        await db.settings.update_one(
            {"user_id": user_id},
            {"$set": kwargs},
            upsert=True
        )
    
    @staticmethod
    async def reset_settings(user_id: int):
        await DatabaseOperations.init_user_settings(user_id)
    
    @staticmethod
    async def create_job(user_id: int, file_id: str, file_type: str, action: str) -> str:
        db = await get_database()
        job = ProcessingJob(
            job_id=str(ObjectId()),
            user_id=user_id,
            file_id=file_id,
            file_type=file_type,
            action=action,
            status="pending"
        )
        result = await db.jobs.insert_one(job.dict())
        return str(result.inserted_id)
    
    @staticmethod
    async def update_job(job_id: str, **kwargs):
        db = await get_database()
        if "status" in kwargs and kwargs["status"] == "completed":
            kwargs["end_time"] = datetime.utcnow()
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": kwargs}
        )
    
    @staticmethod
    async def add_history(user_id: int, action: str, file_type: str, 
                         file_size: int, status: str, processing_time: float):
        db = await get_database()
        history = UserHistory(
            user_id=user_id,
            action=action,
            file_type=file_type,
            file_size=file_size,
            processing_time=processing_time,
            status=status
        )
        await db.history.insert_one(history.dict())
        
        # Update user stats
        await db.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {"total_files": 1, "total_size": file_size},
                "$set": {"last_active": datetime.utcnow()}
            }
        )
    
    @staticmethod
    async def get_user_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        db = await get_database()
        cursor = db.history.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def can_process(user_id: int, file_size: int) -> tuple[bool, str]:
        from config import config
        from utils.premium import is_premium_user
        
        # Check file size
        max_size = config.MAX_FILE_SIZE_PREMIUM if await is_premium_user(user_id) else config.MAX_FILE_SIZE_FREE
        if file_size > max_size:
            return False, f"File too large. Max: {max_size // (1024*1024)}MB"
        
        # Check concurrent jobs
        db = await get_database()
        active_jobs = await db.jobs.count_documents({
            "user_id": user_id,
            "status": {"$in": ["pending", "processing"]}
        })
        
        if active_jobs >= config.MAX_CONCURRENT_JOBS:
            return False, "Too many active jobs"
        
        # Check wait time for free users
        if not await is_premium_user(user_id):
            last_job = await db.jobs.find_one(
                {"user_id": user_id, "status": "completed"},
                sort=[("end_time", -1)]
            )
            
            if last_job and last_job.get("end_time"):
                wait_left = (last_job["end_time"] + timedelta(seconds=config.FREE_USER_WAIT_TIME)) - datetime.utcnow()
                if wait_left.total_seconds() > 0:
                    minutes = int(wait_left.total_seconds() // 60)
                    seconds = int(wait_left.total_seconds() % 60)
                    return False, f"Wait {minutes}m {seconds}s before next file"
        
        return True, ""
