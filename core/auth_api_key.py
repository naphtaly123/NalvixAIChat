# app/core/auth_api_key.py
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
import logging
from core.database import get_db
from models.api_key import APIKey
from models.tenant import Tenant

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

class APIKeyAuth:
    """API Key authentication handler"""
    
    @staticmethod
    async def verify_api_key(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db),
        required_permissions: List[str] = None
    ) -> Tenant:
        """
        Verify API key and return tenant
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        api_key = credentials.credentials
        
        # Check if it's a Bearer token with API key
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        # Hash the provided key for lookup
        import hashlib
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up the API key
        db_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not db_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check expiration
        if db_key.expires_at and db_key.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired"
            )
        
        # Check permissions
        if required_permissions:
            key_permissions = db_key.permissions if isinstance(db_key.permissions, list) else eval(db_key.permissions)
            if not any(perm in key_permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        
        # Update last used timestamp
        db_key.last_used_at = datetime.utcnow()
        db.commit()
        
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.id == db_key.tenant_id).first()
        if not tenant or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant not found or inactive"
            )
        
        return tenant

# Convenience function for chat endpoints
async def get_tenant_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """Get tenant from API key (for chat widget)"""
    return await APIKeyAuth.verify_api_key(credentials, db, required_permissions=["chat"])

# For admin endpoints that might require different permissions
async def get_tenant_admin_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """Get tenant from API key with admin permissions"""
    return await APIKeyAuth.verify_api_key(credentials, db, required_permissions=["admin"])