import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import certifi

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- MongoDB Connection ---
MONGO_URL = os.getenv('MONGO_URL')

_mongodb_client = None

def get_mongodb_client():
    """Get singleton MongoDB client instance."""
    global _mongodb_client
    if _mongodb_client is None:
        if not MONGO_URL:
            raise ValueError("MONGO_URL environment variable is not set")
        _mongodb_client = MongoClient(
            MONGO_URL,
            server_api=ServerApi("1"),
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=30000,
        )
    return _mongodb_client

def get_telegram_auth_collection():
    """Get the telegram_auth collection."""
    client = get_mongodb_client()
    db = client["language_trainer"]
    return db["telegram_auth"]

# --- Rate Limiting (In-Memory) ---
failed_attempts: Dict[int, Dict[str, Any]] = {}

def check_rate_limit(user_id: int) -> bool:
    """Check if user is rate limited for password attempts."""
    current_time = time.time()
    
    if user_id in failed_attempts:
        attempts = failed_attempts[user_id]
        
        # Check if still blocked
        if attempts["count"] >= 5:
            if current_time < attempts["blocked_until"]:
                return False
            else:
                # Block expired, reset
                del failed_attempts[user_id]
    
    return True

def record_failed_attempt(user_id: int):
    """Record a failed login attempt."""
    current_time = time.time()
    
    if user_id not in failed_attempts:
        failed_attempts[user_id] = {"count": 0, "blocked_until": 0}
    
    failed_attempts[user_id]["count"] += 1
    
    # Block for 10 minutes after 5 failed attempts
    if failed_attempts[user_id]["count"] >= 5:
        failed_attempts[user_id]["blocked_until"] = current_time + (10 * 60)  # 10 minutes
        logger.warning(f"User {user_id} blocked for 10 minutes after 5 failed attempts")

def clear_failed_attempts(user_id: int):
    """Clear failed attempts for user after successful login."""
    if user_id in failed_attempts:
        del failed_attempts[user_id]

# --- Password Hashing ---
def create_telegram_password_hash(password: str) -> str:
    """Create secure hash for telegram password."""
    # Use same secret as web app for consistency
    from app import get_cookie_secret
    secret = get_cookie_secret()
    return hashlib.sha256(f"{password}:{secret}".encode()).hexdigest()

# --- Authentication Functions ---
def is_telegram_user_authenticated(user_id: int) -> bool:
    """Check if telegram user is authenticated."""
    try:
        collection = get_telegram_auth_collection()
        user = collection.find_one({"telegram_user_id": user_id})
        
        if user:
            # Update last activity
            collection.update_one(
                {"telegram_user_id": user_id},
                {"$set": {"last_activity": datetime.utcnow()}}
            )
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking telegram user authentication: {e}")
        return False

def authenticate_telegram_user(user_id: int, password: str, user_info) -> bool:
    """Authenticate telegram user with password."""
    try:
        # Check rate limiting
        if not check_rate_limit(user_id):
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # Check password
        auth_password = os.getenv("AUTH_PASSWORD")
        if not auth_password or password != auth_password:
            record_failed_attempt(user_id)
            return False
        
        # Password correct, clear failed attempts
        clear_failed_attempts(user_id)
        
        # Store user in database
        collection = get_telegram_auth_collection()
        password_hash = create_telegram_password_hash(password)
        
        user_data = {
            "telegram_user_id": user_id,
            "authenticated_at": datetime.utcnow(),
            "password_hash": password_hash,
            "last_activity": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Add optional user info if available
        if hasattr(user_info, 'username') and user_info.username:
            user_data["username"] = user_info.username
        
        if hasattr(user_info, 'first_name') and user_info.first_name:
            user_data["first_name"] = user_info.first_name
        
        # Upsert user
        collection.update_one(
            {"telegram_user_id": user_id},
            {"$set": user_data},
            upsert=True
        )
        
        logger.info(f"Successfully authenticated telegram user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error authenticating telegram user: {e}")
        return False

def get_remaining_block_time(user_id: int) -> Optional[int]:
    """Get remaining block time in seconds for rate limited user."""
    if user_id in failed_attempts:
        attempts = failed_attempts[user_id]
        if attempts["count"] >= 5:
            remaining = int(attempts["blocked_until"] - time.time())
            return max(0, remaining)
    return None