from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from datetime import datetime
import pytz

class Database:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("DB_NAME", "telegram_media_bot")
        self.sync_client = MongoClient(self.mongo_uri)
        self.async_client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.async_client[self.db_name]
        self.sync_db = self.sync_client[self.db_name]
        
        self.init_collections()
    
    def init_collections(self):
        # User management
        self.sync_db.users.create_index("user_id", unique=True)
        self.sync_db.users.create_index("is_premium")
        
        # Job collections
        collections = [
            'thumbnail_jobs', 'caption_jobs', 'metadata_jobs', 
            'audio_jobs', 'trim_jobs', 'merge_jobs', 'split_jobs',
            'screenshot_jobs', 'optimize_jobs', 'subtitle_jobs', 'archive_jobs'
        ]
        
        for collection in collections:
            self.sync_db[collection].create_index("user_id")
            self.sync_db[collection].create_index("status")
            self.sync_db[collection].create_index("created_at")
    
    async def get_user(self, user_id):
        return await self.db.users.find_one({"user_id": user_id})
    
    async def create_user(self, user_data):
        user_data['created_at'] = datetime.now(pytz.UTC)
        user_data['is_premium'] = user_data.get('is_premium', False)
        user_data['credits'] = user_data.get('credits', 10)
        return await self.db.users.insert_one(user_data)
    
    async def update_user_credits(self, user_id, credits):
        return await self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"credits": credits}}
        )
    
    async def set_premium_status(self, user_id, is_premium=True):
        return await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_premium": is_premium, "premium_since": datetime.now(pytz.UTC)}}
        )
    
    # Job management
    async def create_job(self, collection, job_data):
        job_data['created_at'] = datetime.now(pytz.UTC)
        job_data['status'] = 'pending'
        result = await self.db[collection].insert_one(job_data)
        return result.inserted_id
    
    async def update_job_status(self, collection, job_id, status, result=None, error=None):
        update_data = {
            "status": status, 
            "updated_at": datetime.now(pytz.UTC)
        }
        if result:
            update_data["result"] = result
        if error:
            update_data["error"] = error
        return await self.db[collection].update_one(
            {"_id": job_id},
            {"$set": update_data}
        )
    
    async def get_user_jobs(self, collection, user_id, limit=10):
        return await self.db[collection].find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit).to_list(length=limit)

db = Database()
