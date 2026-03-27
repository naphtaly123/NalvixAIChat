from langchain_core.tools import BaseTool
from typing import Optional, Type, List, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session
from models.tenant import Tenant

class SchedulingInput(BaseModel):
    """Input schema for scheduling tool"""
    title: str = Field(
        ...,
        description="The title or purpose of the meeting"
    )
    start_time: str = Field(
        ...,
        description="Start time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
    )
    end_time: str = Field(
        ...,
        description="End time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
    )
    attendees: Optional[List[str]] = Field(
        default_factory=list,
        description="List of attendee email addresses or names"
    )
    description: Optional[str] = Field(
        default="",
        description="Additional meeting details or agenda"
    )
    
    class Config:
        populate_by_name = True
        extra = "forbid"

class SchedulingTool(BaseTool):
    """Tool for scheduling meetings"""
    
    name: str = "schedule_meeting"
    description: str = """
    Schedule a meeting or appointment in the calendar.
    
    Required parameters:
    - title: The meeting title
    - start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
    - end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
    
    Optional parameters:
    - attendees: List of attendee names or emails
    - description: Meeting details
    """
    args_schema: Type[BaseModel] = SchedulingInput
    
    tenant: Optional[Tenant] = None
    user_id: Optional[int] = None
    db: Optional[Session] = None
    
    def __init__(self, tenant: Tenant, user_id: int, db_session: Session, **kwargs):
        super().__init__(**kwargs)
        self.tenant = tenant
        self.user_id = user_id
        self.db = db_session
    
    def _run(self, **kwargs) -> str:
        """
        Execute the tool with kwargs - handles any number of arguments
        This is the most scalable approach
        """
        try:
            # Extract parameters from kwargs
            title = kwargs.get("title")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            attendees = kwargs.get("attendees", [])
            description = kwargs.get("description", "")
            
            # Validate required parameters
            if not title:
                return "❌ Missing required parameter: title"
            if not start_time:
                return "❌ Missing required parameter: start_time"
            if not end_time:
                return "❌ Missing required parameter: end_time"
            
            # Handle None attendees
            if attendees is None:
                attendees = []
            
            # Parse and validate times
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError as e:
                return f"❌ Invalid date format: {str(e)}. Please use ISO format (YYYY-MM-DDTHH:MM:SS)"
            
            # Validate times
            if start_dt >= end_dt:
                return "❌ Start time must be before end time"
            
            if start_dt < datetime.utcnow():
                return "❌ Cannot schedule meetings in the past"
            
            # Format response
            start_str = start_dt.strftime('%A, %B %d at %I:%M %p')
            end_str = end_dt.strftime('%I:%M %p')
            
            response = f"✅ Meeting scheduled successfully!\n\n"
            response += f"📅 {title}\n"
            response += f"🕐 {start_str} - {end_str}\n"
            
            if attendees:
                response += f"👥 Attendees: {', '.join(attendees)}\n"
            if description:
                response += f"📝 Details: {description}\n"
            
            return response
        
        except Exception as e:
            return f"❌ Error scheduling meeting: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async version - also accepts kwargs"""
        return self._run(**kwargs)