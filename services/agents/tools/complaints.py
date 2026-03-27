from langchain_core.tools import BaseTool
from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session
from models.tenant import Tenant

class ComplaintsInput(BaseModel):
    """Input schema for complaint tool - MUST match exactly what the LLM will send"""
    complaint_text: str = Field(description="The detailed description of the complaint or issue")
    category: str = Field(description="The category of the complaint: Research, licensing, policy and regulations, standards, numbering, ccTLD, Radio interference, billing, internet speed, Quality of Service, Broadcasting.")
    priority: str = Field(description="The priority level: low, medium, high, or urgent")

class ComplaintsTool(BaseTool):
    """Tool for logging complaints"""
    
    name: str = "log_complaint"
    description: str = """
    Log a complaint or issue in the system.
    
    Use this when users want to:
    - Report a problem
    - File a complaint
    - Submit an issue
    - Request help with something broken
    
    This will create a ticket in the system with a unique ID.
    """
    args_schema: Type[BaseModel] = ComplaintsInput
    
    tenant: Tenant
    user_id: int
    db: Session
    
    def __init__(self, tenant: Tenant, user_id: int, db_session: Session):
        super().__init__(
            tenant=tenant,
            user_id=user_id,
            db=db_session
        )
    
    def _run(self, complaint_text: str, category: str = "general", priority: str = "medium") -> str:
        """Execute the tool"""
        try:
            # Generate ticket ID
            ticket_id = f"TKT-{self.tenant.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Normalize inputs
            category = category.lower().capitalize()
            if category not in ["Research", "Licensing", "Policy and regulations", "Standards", "Numbering", "Cctld", "Radio interference", "Billing", "Internet speed", "Quality of service", "Broadcasting"]:
                category = "General"
            
            priority = priority.lower()
            if priority not in ["low", "medium", "high", "urgent"]:
                priority = "medium"
            
            # Return success response
            return f"""✅ Complaint logged successfully!

📋 Ticket ID: {ticket_id}
📂 Category: {category}
⚡ Priority: {priority.upper()}
📝 Issue: {complaint_text[:100]}{'...' if len(complaint_text) > 100 else ''}

We'll review your complaint and get back to you within 24 hours.
You can check status anytime using ticket ID: {ticket_id}"""
        
        except Exception as e:
            return f"❌ Error logging complaint: {str(e)}"
    
    async def _arun(self, complaint_text: str, category: str = "general", priority: str = "medium") -> str:
        """Async version"""
        return self._run(complaint_text, category, priority)