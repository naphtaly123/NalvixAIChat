# scripts/test_complaint_tool.py
"""
Test script for complaint tool
Run: python scripts/test_complaint_tool.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agents.tools.complaints import ComplaintsTool
from models.tenant import Tenant
from sqlalchemy.orm import Session
from core.database import SessionLocal

def test_complaint_tool():
    """Test the complaint tool directly"""
    db = SessionLocal()
    
    try:
        # Create a mock tenant
        tenant = Tenant(
            id=1,
            name="Test Tenant",
            subdomain="test",
            agent_config={}
        )
        
        # Initialize the tool
        tool = ComplaintsTool(tenant, user_id=1, db_session=db)
        
        # Test with different inputs
        test_cases = [
            "I'm having internet issues, can't connect to VPN",
            "The printer is broken in room 302",
            "I need help with payroll, my salary is incorrect"
        ]
        
        for test in test_cases:
            print(f"\n{'='*50}")
            print(f"Testing: {test}")
            print(f"{'='*50}")
            
            # Call the tool directly
            result = tool._run(
                complaint_text=test,
                category="IT",
                priority="medium"
            )
            print(f"Result: {result}")
    
    finally:
        db.close()

if __name__ == "__main__":
    test_complaint_tool()