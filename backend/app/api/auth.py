# ===========================================
# AuraTask - Authentication API
# ===========================================
# JWT-based authentication with OAuth2

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.notification import NotificationSettings
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    authenticate_user,
)


router = APIRouter()

# OAuth2 scheme for token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ===========================================
# Token Schemas
# ===========================================

class Token(BaseModel):
    """Response schema for login endpoint."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class TokenData(BaseModel):
    """Decoded token payload."""
    user_id: Optional[int] = None
    email: Optional[str] = None


# ===========================================
# JWT Token Functions
# ===========================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data to encode
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT string
        
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id_str = payload.get("sub")
        user_id = int(user_id_str) if user_id_str else None
        email: str = payload.get("email")
        
        if user_id is None:
            print("❌ JWT payload missing 'sub' field")
            return None
        
        return TokenData(user_id=user_id, email=email)
    
    except JWTError as e:
        print(f"❌ JWT Decode Error: {type(e).__name__}: {e}")
        print(f"   SECRET_KEY (first 10 chars): {settings.SECRET_KEY[:10]}...")
        print(f"   ALGORITHM: {settings.ALGORITHM}")
        return None


# ===========================================
# Authentication Dependencies
# ===========================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Validates the JWT token and retrieves the user from database.
    
    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Debug: Print the token we received
    print(f"🔐 Token received: {token[:50]}..." if len(token) > 50 else f"🔐 Token received: {token}")
    
    token_data = decode_access_token(token)
    if token_data is None:
        print("❌ Token decode failed!")
        raise credentials_exception
    
    print(f"✅ Token decoded: user_id={token_data.user_id}, email={token_data.email}")
    
    user = await get_user_by_id(db, token_data.user_id)
    if user is None:
        print(f"❌ User not found for id={token_data.user_id}")
        raise credentials_exception
    
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional version of get_current_user for endpoints that
    work for both authenticated and anonymous users.
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# ===========================================
# Auth Endpoints
# ===========================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    Creates user account and default notification settings.
    """
    try:
        user = await create_user(db, user_data, timezone=user_data.timezone)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    Uses OAuth2 password flow for compatibility with Swagger UI.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Alternative login endpoint accepting JSON body.
    
    For frontends that prefer JSON over form data.
    """
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh the access token for an authenticated user.
    """
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
