from typing import Dict, Optional
from langchain_core.tools import StructuredTool
from services.agents.tools.complaints import ComplaintsTool
from services.agents.tools.scheduling import SchedulingTool
from services.agents.tools.rag_tool import RAGTool
from services.agents.tools.status import StatusTool
from models.tenant import Tenant
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self, tenant: Tenant, user_id: int, db_session: Session):
        self.tenant = tenant
        self.user_id = user_id
        self.db = db_session
        self._tools: Dict[str, StructuredTool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize all available tools"""
        try:
            # Create tool instances
            complaints_tool = ComplaintsTool(self.tenant, self.user_id, self.db)
            scheduling_tool = SchedulingTool(self.tenant, self.user_id, self.db)
            rag_tool = RAGTool(self.tenant, self.user_id, self.db)
            # status_tool = StatusTool(self.tenant, self.user_id, self.db)
            print(f"Initialized tools: {complaints_tool.name}, {scheduling_tool.name}, {rag_tool.name}")
            
            # Convert to LangChain Tools - Use the class attributes directly
            self._tools[complaints_tool.name] = StructuredTool(
                name=complaints_tool.name,  # This is a class attribute, should work
                description=complaints_tool.description,
                func=complaints_tool._run,
                coroutine=complaints_tool._arun,
                args_schema=complaints_tool.args_schema
            )
                   
            self._tools[scheduling_tool.name] = StructuredTool(
                name=scheduling_tool.name,
                description=scheduling_tool.description,
                func=scheduling_tool._run,
                coroutine=scheduling_tool._arun,
                args_schema=scheduling_tool.args_schema
            )
            self._tools[rag_tool.name] = StructuredTool(
                name=rag_tool.name,
                description=rag_tool.description,
                func=rag_tool._run,
                coroutine=rag_tool._arun,
                args_schema=rag_tool.args_schema
            )

            logger.info(f"Tools registered: {list(self._tools.keys())}")
            
        except Exception as e:
            logger.error(f"Error initializing tools: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def get_tool(self, tool_name: str) -> Optional[StructuredTool]:
        """Get a tool by name"""
        tool = self._tools.get(tool_name)
        if tool:
            logger.debug(f"Retrieved tool: {tool_name}")
        else:
            logger.warning(f"Tool not found: {tool_name}. Available: {list(self._tools.keys())}")
        return tool
    
    def get_all_tools(self) -> Dict[str, StructuredTool]:
        """Get all tools"""
        return self._tools