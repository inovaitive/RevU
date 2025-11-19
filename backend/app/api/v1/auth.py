from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from typing import Optional
import uuid
import httpx

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.utils.security import hash_password, verify_password, create_access_token
from app.middleware.auth import get_current_user
from app.config import settings

router = APIRouter()

# Initialize OAuth client
oauth = OAuth()

# Register Google OAuth
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

# Register Microsoft OAuth
if settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET:
    oauth.register(
        name='microsoft',
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        server_metadata_url=f'https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    Automatically creates an organization for the user.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate password is provided for email registration
    if not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for email registration"
        )

    # Create organization for the user
    org = Organization(
        id=uuid.uuid4(),
        name=f"{user_data.full_name or user_data.email}'s Organization",
        tier="free"
    )
    db.add(org)
    db.flush()

    # Create user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        id=uuid.uuid4(),
        organization_id=org.id,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role="admin",  # First user is admin
        oauth_provider="email",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access token
    access_token = create_access_token(
        data={"user_id": str(new_user.id), "organization_id": str(new_user.organization_id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(new_user)
    }


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.
    """
    # Find user
    user = db.query(User).filter(User.email == user_credentials.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user registered via email (not SSO)
    if user.oauth_provider != "email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This account uses {user.oauth_provider} login. Please use SSO."
        )

    # Verify password
    if not user.password_hash or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Create access token
    access_token = create_access_token(
        data={"user_id": str(user.id), "organization_id": str(user.organization_id)}
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return UserResponse.from_orm(current_user)


# Google OAuth endpoints
@router.get("/google/login")
async def google_login():
    """
    Initiate Google OAuth login flow.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )

    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(redirect_uri)


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback.
    """
    try:
        # Exchange code for token
        token = await oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )

        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')

        # Check if user exists
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Create new organization and user
            org = Organization(
                id=uuid.uuid4(),
                name=f"{name}'s Organization",
                tier="free"
            )
            db.add(org)
            db.flush()

            user = User(
                id=uuid.uuid4(),
                organization_id=org.id,
                email=email,
                full_name=name,
                role="admin",
                oauth_provider="google",
                oauth_id=google_id,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update OAuth info if needed
            if not user.oauth_id:
                user.oauth_id = google_id
                user.oauth_provider = "google"
                db.commit()

        # Create access token
        access_token = create_access_token(
            data={"user_id": str(user.id), "organization_id": str(user.organization_id)}
        )

        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


# Microsoft OAuth endpoints
@router.get("/microsoft/login")
async def microsoft_login():
    """
    Initiate Microsoft OAuth login flow.
    """
    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Microsoft OAuth not configured"
        )

    redirect_uri = settings.MICROSOFT_REDIRECT_URI
    return await oauth.microsoft.authorize_redirect(redirect_uri)


@router.get("/microsoft/callback")
async def microsoft_callback(code: str, db: Session = Depends(get_db)):
    """
    Handle Microsoft OAuth callback.
    """
    try:
        # Exchange code for token
        token = await oauth.microsoft.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Microsoft"
            )

        email = user_info.get('email') or user_info.get('preferred_username')
        name = user_info.get('name')
        microsoft_id = user_info.get('sub') or user_info.get('oid')

        # Check if user exists
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Create new organization and user
            org = Organization(
                id=uuid.uuid4(),
                name=f"{name}'s Organization",
                tier="free"
            )
            db.add(org)
            db.flush()

            user = User(
                id=uuid.uuid4(),
                organization_id=org.id,
                email=email,
                full_name=name,
                role="admin",
                oauth_provider="microsoft",
                oauth_id=microsoft_id,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update OAuth info if needed
            if not user.oauth_id:
                user.oauth_id = microsoft_id
                user.oauth_provider = "microsoft"
                db.commit()

        # Create access token
        access_token = create_access_token(
            data={"user_id": str(user.id), "organization_id": str(user.organization_id)}
        )

        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )
