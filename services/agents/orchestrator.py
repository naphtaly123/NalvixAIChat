from typing import Dict, Any, List, Optional
from typer import prompt
import yaml
import os
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq  
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationBufferMemory
from core.config import settings
from services.agents.registry import ToolRegistry
from services.rag.rag import RAGService
from models.tenant import Tenant
import logging

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, tenant: Tenant, user_id: int, db_session):
        self.tenant = tenant
        self.user_id = user_id
        self.db = db_session
        self.tool_registry = ToolRegistry(tenant, user_id, db_session)
        self.rag_service = RAGService(tenant.id)
        
        # Load configuration
        self.agent_config = self._load_agent_config()
        
        # Initialize Groq LLM with function calling support
        self.llm = ChatGroq(
            model=self.agent_config.get("model", settings.GROQ_MODEL),
            temperature=self.agent_config.get("temperature", 0.3),  # Lower temp for better function calling
            api_key=settings.GROQ_API_KEY,
            max_retries=2
        )
        
        # Build tools
        self.tools = self._build_tools()
        
        # Create agent only if tools exist
        if self.tools:
            self.agent = self._create_agent()
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                max_iterations=3,  # Limit iterations
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
        else:
            self.agent = None
            self.agent_executor = None
            logger.warning(f"No tools enabled for tenant {tenant.id}")
    
    def _load_agent_config(self) -> Dict:
        """Load tenant-specific configuration"""
        # Start with default config
        default_config = {
            "system_prompt": "You are a helpful AI assistant that can help with complaints and scheduling.",
            "temperature": 0.3,
            "model": settings.GROQ_MODEL,
            "enabled_tools": ["log_complaint", "schedule_meeting", "rag_retrieval"],
            "custom_instructions": "" 
        }
        
        # Try to load tenant-specific config
        config_path = os.path.join(
            settings.AGENT_CONFIG_PATH, 
            f"tenant_{self.tenant.id}", 
            "agent_config.yaml"
        )
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        default_config.update(config)
            except Exception as e:
                logger.error(f"Error loading config: {str(e)}")
        
        return default_config
    
    def _build_tools(self) -> List[Tool]: 

        """Build tools list"""
        tools = []
        enabled_tools = self.agent_config.get("enabled_tools", [])
    
        # DEBUG: Log what tools are enabled
        logger.info(f"Enabled tools from config: {enabled_tools}")
        print(f"Enabled tools from config: {enabled_tools}")  # Debug print
    
        for tool_name in enabled_tools:
            tool = self.tool_registry.get_tool(tool_name)
            logger.info(f"Looking for tool: {tool_name}, found: {tool is not None}")
            
            if tool:
                tools.append(tool)
                logger.info(f"Added tool: {tool_name}")
                # DEBUG: Print tool details
                print(f"\n=== Tool Debug: {tool_name} ===")
                print(f"Tool type: {type(tool)}")
                print(f"Tool name: {tool.name}")
                print(f"Tool description: {tool.description[:100]}...")
                if hasattr(tool, 'args_schema'):
                    print(f"Args schema: {tool.args_schema.schema()}")
                if hasattr(tool, 'func'):
                    print(f"Has func: {tool.func is not None}")
                print(f"Tool object: {tool}")
            else:
                logger.warning(f"Tool not found: {tool_name}")
    
        # DEBUG: Log all available tools in registry
        all_tools = self.tool_registry.get_all_tools()
        logger.info(f"All available tools in registry: {list(all_tools.keys())}")
        
        # Add RAG tool if enabled
        if "rag_search" in enabled_tools:
            # Create RAG tool
            async def rag_search_async(query: str) -> str:
                result = await self.rag_service.search_and_answer(query)
                return result.get("answer", "No information found.")
            
            def rag_search_sync(query: str) -> str:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(rag_search_async(query))
                finally:
                    loop.close()
            
            tools.append(Tool(
                name="rag_search",
                func=rag_search_sync,
                coroutine=rag_search_async,
                description="Search the knowledge base for information. Use when users ask questions about company policies, procedures, or general information."
            ))
        
        logger.info(f"Total tools built: {len(tools)}")
        return tools


    def _create_agent(self):
        """Create the agent with tenant-specific prompt"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.agent_config.get("system_prompt")),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    
        # Add custom instructions
        custom_instructions = self.agent_config.get("custom_instructions")
        if custom_instructions:
            prompt.messages.insert(1, ("system", custom_instructions))
    
        # Create the agent
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
    
        # Try to get the prompt from the first step
        if hasattr(agent, 'steps') and len(agent.steps) > 0:
            first_step = agent.steps[0]
            print(f"First step type: {type(first_step)}")
        if hasattr(first_step, 'prompt'):
            print(f"Prompt: {first_step.prompt}")
    
        return agent


    async def process_message(self, message: str, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """Process a user message"""
        try:
            if not self.agent_executor:
                return await self._simple_chat(message, conversation_id)
            # Get memory
            memory = None
            if conversation_id:
                memory = await self._load_conversation_memory(conversation_id)
        
            # Run agent with detailed error capture
            logger.info(f"Processing message for tenant {self.tenant.id}: {message[:100]}")
        
            try:
                response = await self.agent_executor.ainvoke({
                    "input": message,
                    "chat_history": memory.messages if memory else []
                    })
                    # Log successful response
                logger.info(f"Agent response successful: {response['output'][:100]}")
            
            except Exception as e:

                # Capture full error details
                error_msg = str(e)
                logger.error(f"Agent execution error: {error_msg}")
            
                # Try to extract failed_generation details
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    logger.error(f"Full API response: {e.response.text}")
            
                # Check for specific error patterns
                if "failed_generation" in error_msg:
                    # Try to get the raw generation
                    if hasattr(e, 'body'):
                        logger.error(f"Error body: {e.body}")
                
                    # Sometimes the error contains JSON with details
                    import json
                    try:
                        # Attempt to extract JSON from error
                        error_start = error_msg.find('{')
                        if error_start != -1:
                            error_json = json.loads(error_msg[error_start:])
                            logger.error(f"Failed generation details: {json.dumps(error_json, indent=2)}")
                    except:
                        pass
    
            
                # Fallback to simple chat
                return await self._simple_chat(message, conversation_id)
        
            # Save conversation
            await self._save_conversation(conversation_id, message, response["output"], response.get("intermediate_steps", []))
        
            return {
                "success": True,
                "response": response["output"],
                "conversation_id": conversation_id,
                "intermediate_steps": response.get("intermediate_steps", [])
                }
    
        except Exception as e:
            logger.error(f"Process error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble processing your request. Could you please rephrase?",
                "conversation_id": conversation_id
                }
 
    async def _simple_chat(self, message: str, conversation_id: Optional[int]) -> Dict[str, Any]:
        """Simple chat without tools"""
        try:
            response = await self.llm.ainvoke([
                {"role": "system", "content": "You are a helpful assistant. Respond naturally to the user."},
                {"role": "user", "content": message}
            ])
            
            return {
                "success": True,
                "response": response.content,
                "conversation_id": conversation_id,
                "intermediate_steps": []
            }
        except Exception as e:
            logger.error(f"Simple chat error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble responding. Please try again.",
                "conversation_id": conversation_id
            }
    
    async def _load_conversation_memory(self, conversation_id: int) -> ConversationBufferMemory:
        """Load conversation memory"""
        memory = ConversationBufferMemory(return_messages=True)
        # TODO: Implement loading from database
        return memory
    
    async def _save_conversation(self, conversation_id: Optional[int], user_message: str, assistant_response: str, intermediate_steps: List):
        """Save conversation"""
        # TODO: Implement saving to database
        pass