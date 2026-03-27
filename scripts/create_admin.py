"""
Script to create initial admin tenant and user
Run: python scripts/create_admin.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from core.security import SecurityService
from models.tenant import Tenant, User
from models.api_key import APIKey
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_tenant_and_user():
    """Create initial admin tenant and user if they don't exist"""
    db = SessionLocal()
    
    try:
        # Check if admin tenant exists
        admin_tenant = db.query(Tenant).filter(Tenant.subdomain == "NalvixAI").first()
        
        if not admin_tenant:
            logger.info("Creating admin tenant...")
            admin_tenant = Tenant(
                name="Super Admin",
                subdomain="NalvixAI",
                agent_config={
                    "system_prompt": "You are an AI assistant for the admin panel.",
                    "enabled_tools": ["rag_search", "admin_tools"]
                },
                is_active=True
            )
            db.add(admin_tenant)
            db.commit()
            db.refresh(admin_tenant)
            logger.info(f"Admin tenant created with ID: {admin_tenant.id}")
        else:
            logger.info(f"Admin tenant already exists with ID: {admin_tenant.id}")
        
        # Check if admin user exists
        admin_user = db.query(User).filter(
            User.email == "superadmin@nalvixai.com",
            User.tenant_id == admin_tenant.id
        ).first()
        
        if not admin_user:
            logger.info("Creating admin user...")
            admin_user = User(
                email="superadmin@nalvixai.com",
                hashed_password=SecurityService.get_password_hash("SuperAdmin123!"),
                full_name="System Administrator",
                tenant_id=admin_tenant.id,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info(f"Admin user created with ID: {admin_user.id}")
            logger.info("Email: superadmin@nalvixai.com")
            logger.info("Password: SuperAdmin123!")
        else:
            logger.info(f"Admin user already exists with ID: {admin_user.id}")
        
        # Create a default API key for the admin tenant
        default_api_key = db.query(APIKey).filter(
            APIKey.tenant_id == admin_tenant.id,
            APIKey.name == "Default Admin Key"
        ).first()
        
        if not default_api_key:
            logger.info("Creating default API key for admin...")
            raw_key, key_hash, key_prefix = APIKey.generate_api_key()
            
            api_key = APIKey(
                tenant_id=admin_tenant.id,
                user_id=admin_user.id,
                name="Default Admin Key",
                key_prefix=key_prefix,
                key_hash=key_hash,
                permissions='["chat", "admin"]',
                is_active=True
            )
            db.add(api_key)
            db.commit()
            logger.info(f"API Key created: {raw_key}")
            logger.info("IMPORTANT: Save this API key! It won't be shown again.")
        else:
            logger.info("Default API key already exists")
        
        logger.info("\n=== Setup Complete ===")
        logger.info("You can now login with:")
        logger.info("Email: superadmin@nalvixai.com")
        logger.info("Password: SuperAdmin123!")
        
    except Exception as e:
        logger.error(f"Error creating admin: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_tenant_and_user()