from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type, Any
from sqlalchemy.orm import Session
from app.models.tenant import Tenant

class BaseTenantTool(BaseTool):
    """Base class for all tenant-aware tools"""
    tenant: Tenant = None
    user_id: int = None
    db: Session = None
    
    def __init__(self, tenant: Tenant, user_id: int, db_session: Session, **kwargs):
        super().__init__(**kwargs)
        self.tenant = tenant
        self.user_id = user_id
        self.db = db_session