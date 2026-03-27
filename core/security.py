# # app/core/security.py
# from datetime import datetime, timedelta
# import hashlib
# from typing import Optional, Dict, Any
# from jose import JWTError, jwt
# from passlib.context import CryptContext
# from fastapi import HTTPException, status, Depends
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from sqlalchemy.orm import Session
# from core.config import settings
# from models.tenant import User, Tenant
# from core.database import get_db
# from core.auth_api_key import get_tenant_from_api_key

# pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
 
# security = HTTPBearer()

# class SecurityService:
#     @staticmethod
#     def verify_password(plain_password: str, hashed_password: str) -> bool:
#         return pwd_context.verify(plain_password, hashed_password)
    
#     @staticmethod
#     def get_password_hash(password: str) -> str:        
#         try:
#             result = pwd_context.hash(password)
#             return result
#         except Exception as e:
#             print(f"Error: {e}")
#             raise
    
#     @staticmethod
#     def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
#         to_encode = data.copy()
#         if expires_delta:
#             expire = datetime.utcnow() + expires_delta
#         else:
#             expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
#         to_encode.update({"exp": expire})
#         encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
#         return encoded_jwt
    
#     @staticmethod
#     def decode_token(token: str) -> Dict[str, Any]:
#         try:
#             payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#             return payload
#         except JWTError:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Could not validate credentials",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
        
# @staticmethod
# async def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
        
#         """Authenticate a user with email and password"""
#         user = db.query(User).filter(User.email == email).first()
#         if not user:
#             return None
#         if not SecurityService.verify_password(password, user.hashed_password):
#             return None
#         if not user.is_active:
#             return None
        
#         # Check if tenant is active
#         if not user.tenant.is_active:
#             return None
        
#         return user

# @staticmethod
# async def get_current_user(
#      credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
#      db: Session = Depends(get_db)
#      ) -> User:
#         """Get current user from JWT token"""
#         if not credentials:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Not authenticated",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
        
#         token = credentials.credentials
#         payload = SecurityService.decode_token(token)
#         user_id: int = payload.get("sub")
#         tenant_id: int = payload.get("tenant_id")
        
#         if user_id is None or tenant_id is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid authentication credentials"
#             )
        
#         user = db.query(User).filter(
#             User.id == user_id,
#             User.tenant_id == tenant_id
#         ).first()
        
#         if user is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="User not found"
#             )
        
#         if not user.is_active:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="User account is inactive"
#             )
        
#         return user

# @staticmethod
# async def get_current_tenant_optional(
#     credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
#     db: Session = Depends(get_db)
#     ) -> Optional[Tenant]:
#         """
#         Get tenant from either JWT token or API key
#         Returns None if no auth provided
#         """
#         if not credentials:
#             return None
        
#         token = credentials.credentials
        
#         # Try JWT first (for authenticated users)
#         try:
#             payload = SecurityService.decode_token(token)
#             user_id = payload.get("sub")
#             tenant_id = payload.get("tenant_id")
            
#             if user_id and tenant_id:
#                 tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
#                 if tenant and tenant.is_active:
#                     return tenant
#         except:
#             # Not a valid JWT, try API key
#             pass
        
#         # Try API key
#         try:
#             return await get_tenant_from_api_key(credentials, db)
#         except:
#             return None

# @staticmethod
# async def get_current_tenant(
#      current_user: User = Depends(get_current_user),
#      db: Session = Depends(get_db)
#      ) -> Tenant:
#         """Get current tenant from user"""
#         tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
#         if not tenant:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Tenant not found"
#             )
        
#         if not tenant.is_active:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Tenant account is inactive"
#             )
        
#         return tenant

# app/core/security.py
from datetime import datetime, timedelta
import hashlib
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.config import settings
from models.tenant import User, Tenant
from core.database import get_db
from core.auth_api_key import get_tenant_from_api_key

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer(auto_error=False)  # Don't auto-error, we'll handle cookie fallback

class SecurityService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:        
        try:
            result = pwd_context.hash(password)
            return result
        except Exception as e:
            print(f"Error: {e}")
            raise
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    async def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not SecurityService.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        
        # Check if tenant is active
        if not user.tenant.is_active:
            return None
        
        return user


async def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Extract token from either Authorization header or cookie.
    Priority: Authorization header > cookie
    """
    # Try Authorization header first
    if credentials:
        return credentials.credentials
    
    # Then try cookie
    token = request.cookies.get("access_token")
    if token:
        return token
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from either JWT token in header or cookie.
    """
    token = await get_token_from_request(request, credentials)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = SecurityService.decode_token(token)
        user_id: int = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        
        if user_id is None or tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Convert user_id to int if it's string
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        user = db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id
        ).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


async def get_current_tenant_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """
    Get tenant from either JWT token, cookie, or API key.
    Returns None if no auth provided.
    """
    token = await get_token_from_request(request, credentials)
    
    if not token:
        return None
    
    # Try JWT first (for authenticated users)
    try:
        payload = SecurityService.decode_token(token)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        
        if user_id and tenant_id:
            if isinstance(user_id, str):
                user_id = int(user_id)
            if isinstance(tenant_id, str):
                tenant_id = int(tenant_id)
                
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant and tenant.is_active:
                return tenant
    except:
        # Not a valid JWT, try API key
        pass
    
    # Try API key (for widget access)
    try:
        return await get_tenant_from_api_key(credentials, db) if credentials else None
    except:
        return None


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Tenant:
    """Get current tenant from user"""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive"
        )
    
    return tenant