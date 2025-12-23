import motor.motor_asyncio
from config import config

class MongoDB:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.db = None
        return cls._instance
    
    async def connect(self):
        """Connect to MongoDB"""
        if self.client is None:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
            self.db = self.client[config.MONGO_DB]
            print(f"Connected to MongoDB: {config.MONGO_URI}")
        return self.db
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
    
    async def get_db(self):
        """Get database instance"""
        if self.db is None:
            await self.connect()
        return self.db

# Singleton instance
mongodb = MongoDB()

async def init_db():
    """Initialize database with indexes"""
    db = await mongodb.get_db()
    
    # Create collections with indexes
    await db.users.create_index("user_id", unique=True)
    await db.settings.create_index("user_id", unique=True)
    await db.history.create_index([("user_id", 1), ("timestamp", -1)])
    await db.jobs.create_index([("user_id", 1), ("status", 1)])
    
    print("Database initialized with indexes")

async def get_database():
    """Get database instance"""
    return await mongodb.get_db()
