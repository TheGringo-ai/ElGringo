"""
JWT Authentication Template
===========================
Complete JWT auth system with login, registration, and protected routes.

Dependencies:
    pip install fastapi python-jose[cryptography] passlib[bcrypt] python-multipart

Usage:
    1. Set SECRET_KEY environment variable
    2. Integrate with your user database
    3. Add protected routes using Depends(get_current_user)
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
import os

app = FastAPI(title="Auth API")

# ============================================================================
# CONFIGURATION
# ============================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ============================================================================
# MODELS
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    id: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(UserBase):
    id: str
    is_active: bool
    is_admin: bool

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

# ============================================================================
# FAKE DATABASE - Replace with real database
# ============================================================================

fake_users_db: dict = {}

def get_user(email: str) -> Optional[UserInDB]:
    if email in fake_users_db:
        return UserInDB(**fake_users_db[email])
    return None

def create_user(user: UserCreate) -> UserInDB:
    import uuid
    user_dict = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": get_password_hash(user.password),
        "is_active": True,
        "is_admin": False,
    }
    fake_users_db[user.email] = user_dict
    return UserInDB(**user_dict)

# ============================================================================
# SECURITY FUNCTIONS
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    user = get_user(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return User(**user.model_dump())

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=User)
async def register(user: UserCreate):
    """Register a new user"""
    if get_user(user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = create_user(user)
    return User(**db_user.model_dump())

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email, "user_id": user.id}
    )

    return Token(access_token=access_token, refresh_token=refresh_token)

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Get new access token using refresh token"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")

        email = payload.get("sub")
        user = get_user(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )

        return Token(access_token=new_access_token, refresh_token=new_refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return current_user

# ============================================================================
# PROTECTED ROUTE EXAMPLES
# ============================================================================

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    """Example protected route"""
    return {"message": f"Hello {current_user.email}!"}

@app.get("/admin")
async def admin_route(admin: User = Depends(get_admin_user)):
    """Example admin-only route"""
    return {"message": f"Hello Admin {admin.email}!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
