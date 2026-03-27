# app/api/v1/endpoints/api_keys.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from models.tenant import Tenant, User
from models.api_key import APIKey
from models.schemas import (
    APIKeyCreate, APIKeyCreateResponse, APIKeyResponse,
    APIKeyUpdate, APIKeyListResponse
)
import logging
from datetime import datetime, timedelta

router = APIRouter(prefix="/api-keys", tags=["API Keys"])
logger = logging.getLogger(__name__)

@router.post("", response_model=APIKeyCreateResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    tenant: Tenant = Depends(get_current_user),  # Only authenticated users can create keys
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the tenant
    """
    try:
        # Generate API key
        raw_key, key_hash, key_prefix = APIKey.generate_api_key()
        
        # Calculate expiration
        expires_at = None
        if key_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
        
        # Create API key record
        api_key = APIKey(
            tenant_id=tenant.id,
            name=key_data.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=str(key_data.permissions),  # Store as string
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        
        # Return with raw key (only shown once!)
        return APIKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            permissions=key_data.permissions,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            is_active=api_key.is_active,
            raw_key=raw_key
        )
    
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating API key: {str(e)}"
        )

@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = 0,
    limit: int = 50,
    tenant: Tenant = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the tenant
    """
    try:
        keys = db.query(APIKey).filter(
            APIKey.tenant_id == tenant.id
        ).offset(skip).limit(limit).all()
        
        total = db.query(APIKey).filter(APIKey.tenant_id == tenant.id).count()
        
        # Parse permissions back to list
        key_responses = []
        for key in keys:
            permissions = key.permissions if isinstance(key.permissions, list) else eval(key.permissions)
            key_responses.append(
                APIKeyResponse(
                    id=key.id,
                    name=key.name,
                    key_prefix=key.key_prefix,
                    permissions=permissions,
                    expires_at=key.expires_at,
                    last_used_at=key.last_used_at,
                    created_at=key.created_at,
                    is_active=key.is_active
                )
            )
        
        return APIKeyListResponse(
            keys=key_responses,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            per_page=limit
        )
    
    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing API keys: {str(e)}"
        )

@router.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: int,
    key_data: APIKeyUpdate,
    tenant: Tenant = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an API key
    """
    try:
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Update fields
        if key_data.name is not None:
            api_key.name = key_data.name
        if key_data.permissions is not None:
            api_key.permissions = str(key_data.permissions)
        if key_data.is_active is not None:
            api_key.is_active = key_data.is_active
        if key_data.expires_at is not None:
            api_key.expires_at = key_data.expires_at
        
        db.commit()
        db.refresh(api_key)
        
        permissions = api_key.permissions if isinstance(api_key.permissions, list) else eval(api_key.permissions)
        
        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            permissions=permissions,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            is_active=api_key.is_active
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating API key: {str(e)}"
        )

@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    tenant: Tenant = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an API key (soft delete - set inactive)
    """
    try:
        api_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Soft delete - just deactivate
        api_key.is_active = False
        db.commit()
        
        return {"message": "API key deactivated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting API key: {str(e)}"
        )

@router.post("/{key_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_api_key(
    key_id: int,
    tenant: Tenant = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate an API key (creates new key, deactivates old one)
    """
    try:
        # Find existing key
        old_key = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id
        ).first()
        
        if not old_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Deactivate old key
        old_key.is_active = False
        
        # Generate new key
        raw_key, key_hash, key_prefix = APIKey.generate_api_key()
        
        # Get permissions from old key
        permissions = old_key.permissions if isinstance(old_key.permissions, list) else eval(old_key.permissions)
        
        # Create new key
        new_key = APIKey(
            tenant_id=tenant.id,
            name=f"{old_key.name} (Regenerated)",
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=str(permissions),
            expires_at=old_key.expires_at,
            is_active=True
        )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        return APIKeyCreateResponse(
            id=new_key.id,
            name=new_key.name,
            key_prefix=new_key.key_prefix,
            permissions=permissions,
            expires_at=new_key.expires_at,
            last_used_at=new_key.last_used_at,
            created_at=new_key.created_at,
            is_active=new_key.is_active,
            raw_key=raw_key
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating API key: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerating API key: {str(e)}"
        )