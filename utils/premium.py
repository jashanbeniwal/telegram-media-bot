from config import config
from database.operations import DatabaseOperations

async def is_premium_user(user_id: int) -> bool:
    """Check if user is premium"""
    # Check config premium IDs
    if user_id in config.PREMIUM_USER_IDS:
        return True
    
    # Check database
    user = await DatabaseOperations.get_user(user_id)
    if user and user.get('tier') == 'premium':
        return True
    
    return False

async def check_wait_time(user_id: int) -> tuple[bool, str]:
    """Check wait time for free users"""
    if await is_premium_user(user_id):
        return True, ""
    
    from datetime import datetime, timedelta
    from database.connection import get_database
    
    db = await get_database()
    
    # Get last completed job
    last_job = await db.jobs.find_one(
        {"user_id": user_id, "status": "completed"},
        sort=[("end_time", -1)]
    )
    
    if not last_job or not last_job.get("end_time"):
        return True, ""
    
    wait_until = last_job["end_time"] + timedelta(seconds=config.FREE_USER_WAIT_TIME)
    now = datetime.utcnow()
    
    if now < wait_until:
        wait_seconds = int((wait_until - now).total_seconds())
        minutes = wait_seconds // 60
        seconds = wait_seconds % 60
        return False, f"⏳ Please wait {minutes}m {seconds}s before next file"
    
    return True, ""

async def get_user_tier(user_id: int) -> str:
    """Get user tier"""
    return "premium" if await is_premium_user(user_id) else "free"

async def get_user_limits(user_id: int) -> dict:
    """Get user limits"""
    premium = await is_premium_user(user_id)
    
    return {
        "max_file_size": config.MAX_FILE_SIZE_PREMIUM if premium else config.MAX_FILE_SIZE_FREE,
        "wait_time": 0 if premium else config.FREE_USER_WAIT_TIME,
        "concurrent_jobs": config.MAX_CONCURRENT_JOBS,
        "tier": "premium" if premium else "free"
    }
