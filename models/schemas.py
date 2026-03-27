import datetime

from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional

from realtime import Enum

#===========================CHAT SCHEMAS=================================================
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[int] = Field(None, description="Existing conversation ID")
    use_rag: bool = Field(True, description="Whether to use RAG for document retrieval")
    top_k: Optional[int] = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response")
    conversation_id: Optional[int] = Field(None, description="Conversation ID")
    success: bool = Field(True, description="Whether the request was successful")
    error: Optional[str] = Field(None, description="Error message if any")
    intermediate_steps: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Agent intermediate steps")
    sources_used: Optional[int] = Field(0, description="Number of sources used (deprecated, use intermediate_steps)")
    rag_used: Optional[bool] = Field(False, description="Whether RAG was used (deprecated)")


# ============ Message Schemas ============
class MessageBase(BaseModel):
    """Base message schema"""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    intermediate_steps: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Agent intermediate steps (for assistant messages)"
    )
    timestamp: Optional[datetime.datetime] = Field(
        default_factory=datetime.datetime.utcnow,
        description="Message timestamp"
    )

class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    pass

class MessageResponse(MessageBase):
    """Schema for message response"""
    id: int
    conversation_id: int
    
    class Config:
        from_attributes = True

class MessageInConversation(BaseModel):
    """Simplified message schema for embedding in conversation"""
    role: str
    content: str
    timestamp: Optional[datetime.datetime] = None
    intermediate_steps: Optional[List[Dict[str, Any]]] = None


# ============ Conversation Schemas ============
class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: Optional[str] = Field("New Conversation", description="Conversation title")
    conversation_metadata: Optional[Dict[str, Any]] = Field( 
        default_factory=dict, 
        description="Additional conversation metadata"
    )

class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation"""
    pass

class ConversationUpdate(BaseModel):
    """Schema for updating conversation"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Conversation title")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_archived: Optional[bool] = Field(None, description="Archive conversation")
    is_pinned: Optional[bool] = Field(None, description="Pin conversation to top")

class ConversationResponse(ConversationBase):
    """Schema for conversation response with full details"""
    id: int
    tenant_id: int
    user_id: int
    messages: List[MessageInConversation] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_archived: bool = Field(default=False)
    is_pinned: bool = Field(default=False)
    message_count: int = Field(0)
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class ConversationSummaryResponse(BaseModel):
    """Schema for conversation list view (without full messages)"""
    id: int
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    message_count: int
    preview: Optional[str] = Field(None, description="Preview of last message (max 150 chars)")
    is_archived: bool = False
    is_pinned: bool = False
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

class ConversationListResponse(BaseModel):
    """Schema for list of conversations"""
    conversations: List[ConversationSummaryResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    """Alias for full conversation detail (same as ConversationResponse)"""
    pass

# ============ Conversation Statistics ============

class ConversationStats(BaseModel):
    """Statistics for a conversation"""
    conversation_id: int
    total_messages: int
    user_messages: int
    assistant_messages: int
    system_messages: Optional[int] = 0
    total_tokens_used: Optional[int] = None
    first_message_at: Optional[datetime.datetime] = None
    last_message_at: Optional[datetime.datetime] = None
    duration_seconds: Optional[float] = None
    average_response_time: Optional[float] = None


# ============ Export Schemas ============
class ConversationExport(BaseModel):
    """Schema for conversation export"""
    conversation_id: int
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[MessageInConversation]
    conversation_metadata: Optional[Dict[str, Any]] = None  # ✅ Changed from 'metadata'
    
    def to_markdown(self) -> str:
        """Convert conversation to markdown format"""
        md = f"# {self.title}\n\n"
        md += f"**Created:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Updated:** {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Messages:** {len(self.messages)}\n\n"
        md += "---\n\n"
        
        for msg in self.messages:
            role = msg["role"].upper()
            content = msg["content"]
            timestamp = msg.get("timestamp")
            if timestamp:
                if isinstance(timestamp, datetime.datetime):
                    timestamp_str = timestamp.strftime('%H:%M:%S')
                else:
                    timestamp_str = str(timestamp)
                md += f"## {role} [{timestamp_str}]\n\n"
            else:
                md += f"## {role}\n\n"
            md += f"{content}\n\n"
        
        return md
    
    def to_text(self) -> str:
        """Convert conversation to plain text format"""
        text = f"Conversation: {self.title}\n"
        text += f"Created: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"Messages: {len(self.messages)}\n"
        text += "=" * 50 + "\n\n"
        
        for msg in self.messages:
            role = msg["role"].upper()
            content = msg["content"]
            timestamp = msg.get("timestamp")
            if timestamp:
                if isinstance(timestamp, datetime.datetime):
                    timestamp_str = timestamp.strftime('%H:%M:%S')
                else:
                    timestamp_str = str(timestamp)
                text += f"[{timestamp_str}] {role}:\n"
            else:
                text += f"{role}:\n"
            text += f"{content}\n\n"
        
        return text
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime.datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime.datetime) else self.updated_at,
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp").isoformat() if isinstance(msg.get("timestamp"), datetime.datetime) else msg.get("timestamp"),
                    "intermediate_steps": msg.get("intermediate_steps")
                }
                for msg in self.messages
            ],
            "conversation_metadata": self.conversation_metadata
        }

#===========================DOCUMENT SCHEMAS=================================================

class DocumentResponse(BaseModel):
    status: str
    document_id: str
    chunks_processed: int

class WebScrapeRequest(BaseModel):
    url: str = Field(..., description="URL to scrape")
    
    class Config:
        from_attributes = True

class DeleteResponse(BaseModel):
    message: str
    count: Optional[int] = None
    deleted_count: Optional[int] = None
    failed_ids: Optional[List[str]] = None

class DocumentInfo(BaseModel):
    id: str
    metadata: dict
    document_preview: str

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_processed: int
    status: str
    tenant_id: Optional[int] = None

class DeleteResponse(BaseModel):
    message: str
    deleted_count: Optional[int] = None
    failed_ids: Optional[List[str]] = None
    tenant_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class DocumentSearchResult(BaseModel):
    text: str
    metadata: dict
    distance: Optional[float] = None

class DocumentSearchResponse(BaseModel):
    query: str
    results: List[DocumentSearchResult]
    count: int
    tenant_id: int

class BatchProcessResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[DocumentResponse]
    tenant_id: Optional[int] = None

class IngestionStatus(BaseModel):
    document_id: str
    tenant_id: int
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None  # Percentage
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============ Tenant Schemas ============

class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Tenant name")
    subdomain: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$", description="Unique subdomain for tenant")
    agent_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent configuration")

class TenantCreate(TenantBase):
    """Schema for creating a new tenant"""
    pass

class TenantUpdate(BaseModel):
    """Schema for updating tenant"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    subdomain: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    agent_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class TenantResponse(TenantBase):
    """Schema for tenant response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # updated_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed=True
        from_attributes = True

class TenantListResponse(BaseModel):
    """Schema for list of tenants"""
    tenants: List[TenantResponse]
    total: int
    page: int
    per_page: int

# ============ User Schemas ============
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    
class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, min_length=1, max_length=200, description="User's full name")
    role: Optional[UserRole] = Field(default=UserRole.USER, description="User role")

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")

class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    tenant_id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        arbitrary_types_allowed=True
        from_attributes = True

class UserListResponse(BaseModel):
    """Schema for list of users"""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int

# ============ Agent Configuration Schemas ============
class AgentConfigBase(BaseModel):
    name: str = Field(..., description="Agent configuration name")
    type: str = Field(..., description="Agent type (e.g., 'tool', 'agent')")
    config: Dict[str, Any] = Field(..., description="Agent configuration details")

class AgentConfigCreate(AgentConfigBase):
    """Schema for creating agent configuration"""
    pass

class AgentConfigUpdate(BaseModel):
    """Schema for updating agent configuration"""
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class AgentConfigResponse(AgentConfigBase):
    """Schema for agent configuration response"""
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        arbitrary_types_allowed=True
        from_attributes = True

# ============ API Key Schemas ============

class APIKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Key name/description")
    permissions: List[str] = Field(default=["chat"], description="List of permissions (chat, admin, etc.)")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days")

class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key"""
    pass

class APIKeyResponse(BaseModel):
    """Schema for API key response (includes raw key only on creation)"""
    id: int
    name: str
    key_prefix: str
    permissions: List[str]
    expires_at: Optional[datetime.datetime]
    last_used_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes raw key)"""
    raw_key: str = Field(..., description="The actual API key - show only once!")
    
    class Config:
        from_attributes = True

class APIKeyUpdate(BaseModel):
    """Schema for updating API key"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime.datetime] = None

class APIKeyListResponse(BaseModel):
    """Schema for list of API keys"""
    keys: List[APIKeyResponse]
    total: int
    page: int
    per_page: int

# ============ Authentication Schemas ============

class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")

class LoginResponse(BaseModel):
    """Schema for login response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="User information")
    tenant: TenantResponse = Field(..., description="Tenant information")

class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request"""
    refresh_token: Optional[str] = Field(None, description="Refresh token (if using refresh tokens)")

class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class ChangePasswordRequest(BaseModel):
    """Schema for password change request"""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""
    token: str
    new_password: str = Field(..., min_length=8)