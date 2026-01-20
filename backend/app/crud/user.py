# ===========================================
# AuraTask - User CRUD Operations
# ===========================================

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from app.models.user import User
from app.schemas.user import UserCreate


# ===========================================
# Password Hashing (using bcrypt directly)
# ===========================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Retrieve a user by their email address.
    
    Args:
        db: Async database session
        email: User's email address
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Retrieve a user by their ID.
    
    Args:
        db: Async database session
        user_id: User's ID
        
    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, 
    user_data: UserCreate,
    timezone: str = "UTC"
) -> User:
    """
    Create a new user with hashed password.
    
    Also creates default notification settings for the user.
    
    Args:
        db: Async database session
        user_data: User creation data (email, password)
        timezone: User's timezone (detected or provided)
        
    Returns:
        Newly created User object
        
    Raises:
        ValueError: If email is already registered
    """
    from app.models.notification import NotificationSettings
    
    # Check if email already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise ValueError("Email already registered")
    
    # Hash the password
    hashed_password = hash_password(user_data.password)
    
    # Create user instance
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        timezone=timezone,
    )
    
    # Add to database
    db.add(user)
    await db.flush()  # Get the ID without committing
    await db.refresh(user)
    
    # Create default notification settings
    notification_settings = NotificationSettings(
        user_id=user.id,
        email_enabled=True,
        email_address=user_data.email,  # Default to registration email
        telegram_enabled=False,
        discord_enabled=False,
        notify_1hr_before=True,
        notify_24hr_before=True,
    )
    db.add(notification_settings)
    await db.flush()
    
    return user


async def update_user_timezone(
    db: AsyncSession,
    user: User,
    timezone: str
) -> User:
    """
    Update a user's timezone preference.
    
    Args:
        db: Async database session
        user: User object to update
        timezone: New timezone string
        
    Returns:
        Updated User object
    """
    user.timezone = timezone
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[User]:
    """
    Authenticate a user by email and password.
    
    Args:
        db: Async database session
        email: User's email
        password: Plain text password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    print(f"[AUTH] Attempting login for: {email}")
    
    user = await get_user_by_email(db, email)
    if not user:
        print(f"[AUTH] ❌ User not found: {email}")
        return None
    
    print(f"[AUTH] User found: {user.email}, checking password...")
    
    password_valid = verify_password(password, user.hashed_password)
    print(f"[AUTH] Password check result: {password_valid}")
    
    if not password_valid:
        print(f"[AUTH] ❌ Password mismatch for: {email}")
        return None
    
    print(f"[AUTH] ✅ Login successful for: {email}")
    return user
