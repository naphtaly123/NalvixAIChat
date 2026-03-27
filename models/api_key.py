# app/models/api_key.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from models.tenant import Base  
from datetime import datetime
import secrets
import hashlib

class APIKey(Base):
    """API Key model for tenant authentication"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Which user created the key
    name = Column(String, nullable=False)
    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String(128), nullable=False, unique=True) 
    permissions = Column(Text, default="[]")  # Store permissions as JSON string (e.g., '["chat", "admin"]')
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")
    
    @staticmethod
    def generate_api_key() -> tuple:
        """Generate a new API key and its hash"""
        # Format: tk_ (tenant key) + 32 random chars
        raw_key = f"tk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]
        return raw_key, key_hash, key_prefix
    
    def verify_key(self, raw_key: str) -> bool:
        """Verify if the provided raw key matches the stored hash"""
        return hashlib.sha256(raw_key.encode()).hexdigest() == self.key_hash