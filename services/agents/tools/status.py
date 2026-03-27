# app/services/agents/tools/status.py
from langchain.tools import BaseTool
from typing import Optional, Type
from pydantic import BaseModel, Field, PrivateAttr
from sqlalchemy.orm import Session
from models.tenant import Tenant

class StatusInput(BaseModel):
    """Input for status tool"""
    ticket_id: str = Field(description="Ticket ID to check status")

class StatusTool(BaseTool):
    """Tool for checking ticket/order status"""
    
    name: str = "check_status"
    description: str = "Check the status of a ticket, order, or request. Use this when users want to know the status of their previous requests or complaints."
    args_schema: Type[BaseModel] = StatusInput
    
    _tenant: Tenant = PrivateAttr()
    _user_id: int = PrivateAttr()
    _db: Session = PrivateAttr()
    
    def __init__(self, tenant: Tenant, user_id: int, db_session: Session, **kwargs):
        super().__init__(**kwargs)
        self._tenant = tenant
        self._user_id = user_id
        self._db = db_session
    
    def _run(self, ticket_id: str) -> str:
        """Check status of a ticket"""
        try:
            # Query database for ticket status (uncomment when you have model)
            # from app.models.complaint import Complaint
            # complaint = self._db.query(Complaint).filter(
            #     Complaint.ticket_id == ticket_id,
            #     Complaint.tenant_id == self._tenant.id
            # ).first()
            #
            # if complaint:
            #     return f"📋 Ticket {ticket_id}\nStatus: {complaint.status}\nCreated: {complaint.created_at}\nPriority: {complaint.priority}\nCategory: {complaint.category}"
            # else:
            #     return f"❌ Ticket {ticket_id} not found. Please check the ticket ID and try again."
            
            # Mock response for now
            return f"📋 Ticket {ticket_id} Status\n\nStatus: In Progress\nPriority: Medium\nCreated: Just now\nEstimated completion: 2 hours\n\nWe'll notify you when there's an update."
        
        except Exception as e:
            return f"❌ Error checking status: {str(e)}"
    
    async def _arun(self, ticket_id: str) -> str:
        """Async version of the tool"""
        return self._run(ticket_id)