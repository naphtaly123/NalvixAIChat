# # app/api/v1/endpoints/admin.py
# from fastapi import APIRouter, Depends, HTTPException, status
# from typing import List
# from sqlalchemy.orm import Session
# from core.database import get_db
# from core.security import get_current_user, SecurityService
# from models.tenant import Tenant, User
# from models.schemas import TenantCreate, TenantResponse, UserCreate, UserResponse
# from api.v1 import api_keys
# from services.rag.vector_store import TenantAwareVectorStore
# import logging

# router = APIRouter()
# logger = logging.getLogger(__name__)

# router.include_router(api_keys.router)

# @router.post("/tenants", response_model=TenantResponse)
# async def create_tenant(
#     tenant_data: TenantCreate,
#     db: Session = Depends(get_db)
# ):
#     """Create a new tenant (superadmin only)"""
#     try:
#         # Check if tenant exists
#         existing = db.query(Tenant).filter(
#             (Tenant.name == tenant_data.name) | 
#             (Tenant.subdomain == tenant_data.subdomain)
#         ).first()
        
#         if existing:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Tenant with this name or subdomain already exists"
#             )
        
#         # Create tenant
#         tenant = Tenant(
#             name=tenant_data.name,
#             subdomain=tenant_data.subdomain,
#             agent_config=tenant_data.agent_config or {}
#         )
        
#         db.add(tenant)
#         db.commit()
#         db.refresh(tenant)
        
#         # Initialize vector store collections
#         vector_store = TenantAwareVectorStore()
#         vector_store.get_or_create_collection(tenant.id)
        
#         return tenant
    
#     except Exception as e:
#         logger.error(f"Error creating tenant: {str(e)}")
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )

# @router.post("/tenants/{tenant_id}/users", response_model=UserResponse)
# async def create_user(
#     tenant_id: int,
#     user_data: UserCreate,
#     db: Session = Depends(get_db)
# ):
#     """Create a user for a specific tenant"""
#     try:
#         # Check if tenant exists
#         tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
#         if not tenant:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Tenant not found"
#             )
        
#         # Check if user exists
#         existing = db.query(User).filter(User.email == user_data.email).first()
#         if existing:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User with this email already exists"
#             )
        
#         # Create user
#         user = User(
#             email=user_data.email,
#             hashed_password=SecurityService.get_password_hash(user_data.password),
#             full_name=user_data.full_name,
#             tenant_id=tenant_id
#         )
        
#         db.add(user)
#         db.commit()
#         db.refresh(user)
        
#         return user
    
#     except Exception as e:
#         logger.error(f"Error creating user: {str(e)}")
#         db.rollback()
#         raise

# @router.get("/tenants/{tenant_id}/config")
# async def get_tenant_config(
#     tenant_id: int,
#     db: Session = Depends(get_db)
# ):
#     """Get tenant configuration"""
#     tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
#     if not tenant:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Tenant not found"
#         )
    
#     return {
#         "id": tenant.id,
#         "name": tenant.name,
#         "subdomain": tenant.subdomain,
#         "agent_config": tenant.agent_config,
#         "is_active": tenant.is_active
#     }

# @router.put("/tenants/{tenant_id}/config")
# async def update_tenant_config(
#     tenant_id: int,
#     config: dict,
#     db: Session = Depends(get_db)
# ):
#     """Update tenant configuration"""
#     tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
#     if not tenant:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Tenant not found"
#         )
    
#     tenant.agent_config = config
#     db.commit()
    
#     return {"message": "Configuration updated successfully"}



# app/api/v1/endpoints/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from core.config import settings
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user, SecurityService
from models.tenant import Tenant, User
from models.schemas import TenantCreate, TenantResponse, UserCreate, UserResponse
from api.v1 import api_keys
from services.rag.vector_store import TenantAwareVectorStore
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

router.include_router(api_keys.router)


# Add login request/response models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    tenant: TenantResponse

router = APIRouter()
logger = logging.getLogger(__name__)

router.include_router(api_keys.router)

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login endpoint that returns JWT token and sets HTTP-only cookie.
    This is the main authentication endpoint for admin users.
    """
    try:
        # Authenticate user
        user = await SecurityService.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            db=db
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Set token expiration
        if login_data.remember_me:
            expires_delta = timedelta(days=30)  # 30 days for "remember me"
        else:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Create access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": user.tenant_id,
            "role": user.role or "admin"
        }
        
        access_token = SecurityService.create_access_token(
            data=token_data,
            expires_delta=expires_delta
        )
        
        # Set HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,  # Set to False for local development without HTTPS
            samesite="lax",
            max_age=expires_delta.total_seconds(),
            path="/"
        )
        
        # Get tenant details
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            user=UserResponse.from_orm(user),
            tenant=TenantResponse.from_orm(tenant) if tenant else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    Logout endpoint that clears the authentication cookie.
    """
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    Useful for checking login status and user details.
    """
    return current_user

@router.get("/check-auth")
async def check_auth(
    current_user: User = Depends(get_current_user)
):
    """
    Check if user is authenticated.
    Returns user info if authenticated, 401 if not.
    """
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role
    }


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db)
):
    """Create a new tenant (superadmin only)"""
    try:
        # Check if tenant exists
        existing = db.query(Tenant).filter(
            (Tenant.name == tenant_data.name) | 
            (Tenant.subdomain == tenant_data.subdomain)
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant with this name or subdomain already exists"
            )
        
        # Create tenant
        tenant = Tenant(
            name=tenant_data.name,
            subdomain=tenant_data.subdomain,
            agent_config=tenant_data.agent_config or {}
        )
        
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        # Initialize vector store collections
        vector_store = TenantAwareVectorStore()
        vector_store.get_or_create_collection(tenant.id)
        
        return tenant
    
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/tenants/{tenant_id}/users", response_model=UserResponse)
async def create_user(
    tenant_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a user for a specific tenant"""
    try:
        # Check if tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Check if user exists
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create user
        user = User(
            email=user_data.email,
            hashed_password=SecurityService.get_password_hash(user_data.password),
            full_name=user_data.full_name,
            tenant_id=tenant_id
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise

@router.get("/tenants/{tenant_id}/config")
async def get_tenant_config(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get tenant configuration"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "subdomain": tenant.subdomain,
        "agent_config": tenant.agent_config,
        "is_active": tenant.is_active
    }

@router.put("/tenants/{tenant_id}/config")
async def update_tenant_config(
    tenant_id: int,
    config: dict,
    db: Session = Depends(get_db)
):
    """Update tenant configuration"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant.agent_config = config
    db.commit()
    
    return {"message": "Configuration updated successfully"}