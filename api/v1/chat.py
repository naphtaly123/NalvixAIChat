# from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
# from sqlalchemy.orm import Session
# from typing import Optional
# from models.schemas import ChatRequest, ChatResponse, ConversationResponse, ConversationListResponse
# from core.auth_api_key import get_tenant_from_api_key
# from services.agents.orchestrator import AgentOrchestrator
# from services.rag.rag import get_rag_service
# from core.database import get_db
# from core.security import get_current_tenant, get_current_user
# from models.tenant import Tenant, User
# from models.conversation import Conversation
# import logging
# from datetime import datetime

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/chat", tags=["Chat"])

# @router.post("", response_model=ChatResponse)
# async def chat_endpoint(
#     req: ChatRequest,
#     background_tasks: BackgroundTasks,
#     tenant: Tenant = Depends(get_tenant_from_api_key),  # Use API key auth
#     db: Session = Depends(get_db)
# ):
#     """
#     Process a chat message with the AI agent.
#     Authentication: API key in Bearer header
#     """
#     try:
#         # Note: No user_id here because it's coming from widget
#         # We'll create a virtual user or use tenant default
#         user = await get_or_create_default_user(tenant.id, db)
        
#         # Initialize agent orchestrator
#         orchestrator = AgentOrchestrator(tenant, user.id, db)
        
#         # Process message
#         result = await orchestrator.process_message(
#             message=req.message,
#             conversation_id=req.conversation_id
#         )
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=500,
#                 detail=result.get("error", "Error processing message")
#             )
        
#         return ChatResponse(
#             response=result["response"],
#             conversation_id=result["conversation_id"],
#             success=True,
#             intermediate_steps=result.get("intermediate_steps", [])
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Chat endpoint error for tenant {tenant.id}: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error processing chat: {str(e)}"
#         )
    
# async def get_or_create_default_user(tenant_id: int, db: Session) -> User:
#     """Get or create a default user for API key access"""
#     # Check if there's a default widget user
#     default_user = db.query(User).filter(
#         User.tenant_id == tenant_id,
#         User.email == f"widget_{tenant_id}@internal.local"
#     ).first()
    
#     if not default_user:
#         # Create default widget user
#         default_user = User(
#             email=f"widget_{tenant_id}@internal.local",
#             full_name="Widget User",
#             hashed_password="",  # No password for widget user
#             tenant_id=tenant_id,
#             is_active=True
#         )
#         db.add(default_user)
#         db.commit()
#         db.refresh(default_user)
    
#     return default_user

# @router.post("/simple", response_model=ChatResponse)
# async def simple_chat_endpoint(
#     req: ChatRequest,
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Simple chat endpoint without agent orchestration.
#     Uses only RAG for document retrieval.
#     """
#     try:
#         rag_service = get_rag_service(tenant.id)
        
#         if req.use_rag:
#             # Use RAG with document retrieval
#             result = await rag_service.search_and_answer(
#                 query=req.message,
#                 conversation_history=req.context.get("conversation_history") if req.context else None,
#                 top_k=req.top_k
#             )
            
#             return ChatResponse(
#                 response=result["answer"],
#                 conversation_id=req.conversation_id,
#                 success=True,
#                 intermediate_steps=[{
#                     "type": "rag",
#                     "chunks_used": result.get("chunks_used", 0),
#                     "sources": result.get("sources", [])
#                 }]
#             )
#         else:
#             # Direct chat without RAG
#             response = await rag_service.llm.generate_response([{
#                 "role": "user",
#                 "content": req.message
#             }])
            
#             return ChatResponse(
#                 response=response,
#                 conversation_id=req.conversation_id,
#                 success=True,
#                 intermediate_steps=[]
#             )
    
#     except Exception as e:
#         logger.error(f"Simple chat error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error processing chat: {str(e)}"
#         )

# @router.get("/conversations", response_model=ConversationListResponse)
# async def list_conversations(
#     skip: int = 0,
#     limit: int = 50,
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     List all conversations for the current user
#     """
#     try:
#         conversations = db.query(Conversation).filter(
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
        
#         total = db.query(Conversation).filter(
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).count()
        
#         # Format conversations without loading all messages
#         conversation_list = []
#         for conv in conversations:
#             conversation_list.append({
#                 "id": conv.id,
#                 "title": conv.title,
#                 "created_at": conv.created_at,
#                 "updated_at": conv.updated_at,
#                 "message_count": len(conv.messages) if conv.messages else 0,
#                 "preview": conv.messages[-1]["content"][:100] + "..." if conv.messages and len(conv.messages[-1]["content"]) > 100 else conv.messages[-1]["content"] if conv.messages else ""
#             })
        
#         return ConversationListResponse(
#             conversations=conversation_list,
#             total=total,
#             page=skip // limit + 1 if limit > 0 else 1,
#             per_page=limit
#         )
    
#     except Exception as e:
#         logger.error(f"Error listing conversations: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error listing conversations: {str(e)}"
#         )

# @router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
# async def get_conversation(
#     conversation_id: int,
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get a specific conversation with all messages
#     """
#     try:
#         conversation = db.query(Conversation).filter(
#             Conversation.id == conversation_id,
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).first()
        
#         if not conversation:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found"
#             )
        
#         return conversation
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting conversation: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error getting conversation: {str(e)}"
#         )

# @router.delete("/conversations/{conversation_id}")
# async def delete_conversation(
#     conversation_id: int,
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Delete a conversation
#     """
#     try:
#         conversation = db.query(Conversation).filter(
#             Conversation.id == conversation_id,
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).first()
        
#         if not conversation:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found"
#             )
        
#         db.delete(conversation)
#         db.commit()
        
#         return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error deleting conversation: {str(e)}")
#         db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error deleting conversation: {str(e)}"
#         )

# @router.put("/conversations/{conversation_id}/title")
# async def update_conversation_title(
#     conversation_id: int,
#     title: str,
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Update conversation title
#     """
#     try:
#         conversation = db.query(Conversation).filter(
#             Conversation.id == conversation_id,
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).first()
        
#         if not conversation:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found"
#             )
        
#         conversation.title = title
#         conversation.updated_at = datetime.utcnow()
#         db.commit()
        
#         return {"message": "Title updated successfully", "title": title}
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error updating conversation title: {str(e)}")
#         db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error updating title: {str(e)}"
#         )

# @router.post("/conversations/{conversation_id}/messages")
# async def add_message_to_conversation(
#     conversation_id: int,
#     message: ChatRequest,
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Add a message to an existing conversation and get response
#     """
#     try:
#         # Check if conversation exists and belongs to user
#         conversation = db.query(Conversation).filter(
#             Conversation.id == conversation_id,
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).first()
        
#         if not conversation:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found"
#             )
        
#         # Initialize orchestrator
#         orchestrator = AgentOrchestrator(tenant, user.id, db)
        
#         # Process message with existing conversation
#         result = await orchestrator.process_message(
#             message=message.message,
#             conversation_id=conversation_id
#         )
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=500,
#                 detail=result.get("error", "Error processing message")
#             )
        
#         return ChatResponse(
#             response=result["response"],
#             conversation_id=conversation_id,
#             success=True,
#             intermediate_steps=result.get("intermediate_steps", [])
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error adding message: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error adding message: {str(e)}"
#         )

# @router.get("/conversations/{conversation_id}/export")
# async def export_conversation(
#     conversation_id: int,
#     format: str = "json",
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Export conversation in different formats (json, txt, markdown)
#     """
#     try:
#         conversation = db.query(Conversation).filter(
#             Conversation.id == conversation_id,
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).first()
        
#         if not conversation:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found"
#             )
        
#         if format == "json":
#             return conversation.messages
        
#         elif format == "txt":
#             # Generate plain text format
#             text = f"Conversation: {conversation.title}\n"
#             text += f"Date: {conversation.created_at}\n\n"
            
#             for msg in conversation.messages:
#                 role = msg.get("role", "unknown").upper()
#                 content = msg.get("content", "")
#                 text += f"{role}: {content}\n\n"
            
#             return {"content": text, "format": "txt"}
        
#         elif format == "markdown":
#             # Generate markdown format
#             markdown = f"# {conversation.title}\n\n"
#             markdown += f"**Date:** {conversation.created_at}\n\n"
#             markdown += "---\n\n"
            
#             for msg in conversation.messages:
#                 role = msg.get("role", "unknown")
#                 content = msg.get("content", "")
                
#                 if role == "user":
#                     markdown += f"**User:**\n{content}\n\n"
#                 elif role == "assistant":
#                     markdown += f"**Assistant:**\n{content}\n\n"
#                 else:
#                     markdown += f"**{role.capitalize()}:**\n{content}\n\n"
            
#             return {"content": markdown, "format": "markdown"}
        
#         else:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid format. Supported: json, txt, markdown"
#             )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error exporting conversation: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error exporting conversation: {str(e)}"
#         )

# @router.get("/stats")
# async def get_chat_stats(
#     tenant: Tenant = Depends(get_current_tenant),
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get chat statistics for the current user
#     """
#     try:
#         # Get total conversations
#         total_conversations = db.query(Conversation).filter(
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).count()
        
#         # Get messages count
#         all_conversations = db.query(Conversation).filter(
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id
#         ).all()
        
#         total_messages = 0
#         for conv in all_conversations:
#             total_messages += len(conv.messages) if conv.messages else 0
        
#         # Get last 7 days activity
#         from datetime import timedelta
#         week_ago = datetime.utcnow() - timedelta(days=7)
        
#         recent_activity = db.query(Conversation).filter(
#             Conversation.tenant_id == tenant.id,
#             Conversation.user_id == user.id,
#             Conversation.updated_at >= week_ago
#         ).count()
        
#         return {
#             "total_conversations": total_conversations,
#             "total_messages": total_messages,
#             "recent_activity_7d": recent_activity,
#             "tenant_id": tenant.id,
#             "user_id": user.id
#         }
    
#     except Exception as e:
#         logger.error(f"Error getting chat stats: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error getting statistics: {str(e)}"
#         )


from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from models.schemas import ChatRequest, ChatResponse, ConversationResponse, ConversationListResponse
from core.auth_api_key import get_tenant_from_api_key
from services.agents.orchestrator import AgentOrchestrator
from services.rag.rag import get_rag_service
from core.database import get_db
from core.security import get_current_tenant, get_current_user
from models.tenant import Tenant, User
from models.conversation import Conversation
import logging
from datetime import datetime
from langchain_core.agents import AgentAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Chat"])

def format_intermediate_steps(intermediate_steps: List[Any]) -> List[Dict[str, Any]]:
    """
    Format intermediate steps to ensure they're JSON serializable.
    Converts tuples (AgentAction, result) to dictionaries.
    """
    if not intermediate_steps:
        return []
    
    formatted_steps = []
    
    for step in intermediate_steps:
        # Case 1: Step is a tuple (AgentAction, result)
        if isinstance(step, tuple) and len(step) == 2:
            action, result = step
            
            # Format the action part
            if isinstance(action, AgentAction):
                action_dict = {
                    "tool": action.tool,
                    "tool_input": action.tool_input,
                    "log": action.log
                }
            elif hasattr(action, 'tool') and hasattr(action, 'tool_input'):
                # Handle ToolAgentAction or similar
                action_dict = {
                    "tool": getattr(action, 'tool', 'unknown'),
                    "tool_input": getattr(action, 'tool_input', {}),
                    "log": getattr(action, 'log', '')
                }
            else:
                action_dict = {"raw_action": str(action)}
            
            formatted_steps.append({
                "action": action_dict,
                "observation": str(result) if result else ""
            })
        
        # Case 2: Step is already a dictionary
        elif isinstance(step, dict):
            formatted_steps.append(step)
        
        # Case 3: Step is something else
        else:
            formatted_steps.append({"raw": str(step)})
    
    return formatted_steps

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    tenant: Tenant = Depends(get_tenant_from_api_key),
    db: Session = Depends(get_db)
):
    """
    Process a chat message with the AI agent.
    Authentication: API key in Bearer header
    """
    try:
        # Note: No user_id here because it's coming from widget
        # We'll create a virtual user or use tenant default
        user = await get_or_create_default_user(tenant.id, db)
        
        # Initialize agent orchestrator
        orchestrator = AgentOrchestrator(tenant, user.id, db)
        
        # Process message
        result = await orchestrator.process_message(
            message=req.message,
            conversation_id=req.conversation_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error processing message")
            )
        
        # Format intermediate steps to ensure they're JSON serializable
        formatted_steps = format_intermediate_steps(result.get("intermediate_steps", []))
        
        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            success=True,
            intermediate_steps=formatted_steps
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error for tenant {tenant.id}: {str(e)}")
        # Log the full error with traceback for debugging
        logger.exception(f"Full error details for tenant {tenant.id}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )
# async def chat_endpoint(
#     req: ChatRequest,
#     background_tasks: BackgroundTasks,
#     tenant: Tenant = Depends(get_tenant_from_api_key),  # Use API key auth
#     db: Session = Depends(get_db)
# ):
#     """
#     Process a chat message with the AI agent.
#     Authentication: API key in Bearer header
#     """
#     try:
#         # Note: No user_id here because it's coming from widget
#         # We'll create a virtual user or use tenant default
#         user = await get_or_create_default_user(tenant.id, db)
        
#         # Initialize agent orchestrator
#         orchestrator = AgentOrchestrator(tenant, user.id, db)
        
#         # Process message
#         result = await orchestrator.process_message(
#             message=req.message,
#             conversation_id=req.conversation_id
#         )
        
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=500,
#                 detail=result.get("error", "Error processing message")
#             )
        
#         return ChatResponse(
#             response=result["response"],
#             conversation_id=result["conversation_id"],
#             success=True,
#             intermediate_steps=result.get("intermediate_steps", [])
#         )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Chat endpoint error for tenant {tenant.id}: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error processing chat: {str(e)}"
#         )
    
async def get_or_create_default_user(tenant_id: int, db: Session) -> User:
    """Get or create a default user for API key access"""
    # Check if there's a default widget user
    default_user = db.query(User).filter(
        User.tenant_id == tenant_id,
        User.email == f"widget_{tenant_id}@internal.local"
    ).first()
    
    if not default_user:
        # Create default widget user
        default_user = User(
            email=f"widget_{tenant_id}@internal.local",
            full_name="Widget User",
            hashed_password="",  # No password for widget user
            tenant_id=tenant_id,
            is_active=True
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
    
    return default_user

@router.post("/simple", response_model=ChatResponse)
async def simple_chat_endpoint(
    req: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simple chat endpoint without agent orchestration.
    Uses only RAG for document retrieval.
    """
    try:
        rag_service = get_rag_service(tenant.id)
        
        if req.use_rag:
            # Use RAG with document retrieval
            result = await rag_service.search_and_answer(
                query=req.message,
                conversation_history=req.context.get("conversation_history") if req.context else None,
                top_k=req.top_k
            )
            
            return ChatResponse(
                response=result["answer"],
                conversation_id=req.conversation_id,
                success=True,
                intermediate_steps=[{
                    "type": "rag",
                    "chunks_used": result.get("chunks_used", 0),
                    "sources": result.get("sources", [])
                }]
            )
        else:
            # Direct chat without RAG
            response = await rag_service.llm.generate_response([{
                "role": "user",
                "content": req.message
            }])
            
            return ChatResponse(
                response=response,
                conversation_id=req.conversation_id,
                success=True,
                intermediate_steps=[]
            )
    
    except Exception as e:
        logger.error(f"Simple chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all conversations for the current user
    """
    try:
        conversations = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
        
        total = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).count()
        
        # Format conversations without loading all messages
        conversation_list = []
        for conv in conversations:
            conversation_list.append({
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": len(conv.messages) if conv.messages else 0,
                "preview": conv.messages[-1]["content"][:100] + "..." if conv.messages and len(conv.messages[-1]["content"]) > 100 else conv.messages[-1]["content"] if conv.messages else ""
            })
        
        return ConversationListResponse(
            conversations=conversation_list,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            per_page=limit
        )
    
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation with all messages
    """
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        return conversation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting conversation: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation
    """
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        db.delete(conversation)
        db.commit()
        
        return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting conversation: {str(e)}"
        )

@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int,
    title: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update conversation title
    """
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Title updated successfully", "title": title}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation title: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating title: {str(e)}"
        )

@router.post("/conversations/{conversation_id}/messages")
async def add_message_to_conversation(
    conversation_id: int,
    message: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a message to an existing conversation and get response
    """
    try:
        # Check if conversation exists and belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        # Initialize orchestrator
        orchestrator = AgentOrchestrator(tenant, user.id, db)
        
        # Process message with existing conversation
        result = await orchestrator.process_message(
            message=message.message,
            conversation_id=conversation_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error processing message")
            )
        
        return ChatResponse(
            response=result["response"],
            conversation_id=conversation_id,
            success=True,
            intermediate_steps=result.get("intermediate_steps", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error adding message: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: int,
    format: str = "json",
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export conversation in different formats (json, txt, markdown)
    """
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        if format == "json":
            return conversation.messages
        
        elif format == "txt":
            # Generate plain text format
            text = f"Conversation: {conversation.title}\n"
            text += f"Date: {conversation.created_at}\n\n"
            
            for msg in conversation.messages:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                text += f"{role}: {content}\n\n"
            
            return {"content": text, "format": "txt"}
        
        elif format == "markdown":
            # Generate markdown format
            markdown = f"# {conversation.title}\n\n"
            markdown += f"**Date:** {conversation.created_at}\n\n"
            markdown += "---\n\n"
            
            for msg in conversation.messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                
                if role == "user":
                    markdown += f"**User:**\n{content}\n\n"
                elif role == "assistant":
                    markdown += f"**Assistant:**\n{content}\n\n"
                else:
                    markdown += f"**{role.capitalize()}:**\n{content}\n\n"
            
            return {"content": markdown, "format": "markdown"}
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Supported: json, txt, markdown"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting conversation: {str(e)}"
        )

@router.get("/stats")
async def get_chat_stats(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get chat statistics for the current user
    """
    try:
        # Get total conversations
        total_conversations = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).count()
        
        # Get messages count
        all_conversations = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id
        ).all()
        
        total_messages = 0
        for conv in all_conversations:
            total_messages += len(conv.messages) if conv.messages else 0
        
        # Get last 7 days activity
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_activity = db.query(Conversation).filter(
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id,
            Conversation.updated_at >= week_ago
        ).count()
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "recent_activity_7d": recent_activity,
            "tenant_id": tenant.id,
            "user_id": user.id
        }
    
    except Exception as e:
        logger.error(f"Error getting chat stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting statistics: {str(e)}"
        )