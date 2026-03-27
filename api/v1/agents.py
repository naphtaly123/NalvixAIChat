# app/api/v1/endpoints/agents.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_tenant, get_current_user
from models.tenant import Tenant, User, AgentConfig
from models.schemas import AgentConfigCreate, AgentConfigResponse
import yaml
import os
from core.config import settings

router = APIRouter()

@router.get("/configs")
async def list_agent_configs(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List all agent configurations for the tenant"""
    configs = db.query(AgentConfig).filter(
        AgentConfig.tenant_id == tenant.id,
        AgentConfig.is_active == True
    ).all()
    
    return configs

@router.post("/configs")
async def create_agent_config(
    config_data: AgentConfigCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create a new agent configuration"""
    config = AgentConfig(
        tenant_id=tenant.id,
        name=config_data.name,
        type=config_data.type,
        config=config_data.config
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return config

@router.put("/configs/{config_id}")
async def update_agent_config(
    config_id: int,
    config_data: Dict,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update an agent configuration"""
    config = db.query(AgentConfig).filter(
        AgentConfig.id == config_id,
        AgentConfig.tenant_id == tenant.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    config.config.update(config_data)
    config.is_active = config_data.get("is_active", config.is_active)
    
    db.commit()
    
    return config

@router.get("/reload")
async def reload_agent_configs(
    tenant: Tenant = Depends(get_current_tenant)
):
    """Reload agent configurations from YAML files"""
    config_path = os.path.join(
        settings.AGENT_CONFIG_PATH,
        f"tenant_{tenant.id}",
        "agent_config.yaml"
    )
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            tenant.agent_config = config
            # Save to database
            # This would need a db session
    
    return {"message": "Configuration reloaded"}