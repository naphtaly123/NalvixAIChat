# scripts/verify_migration.py
from app.core.database import SessionLocal
from sqlalchemy import inspect, text

def verify_migration():
    db = SessionLocal()
    try:
        # Check alembic version
        result = db.execute(text("SELECT * FROM alembic_version"))
        version = result.fetchone()
        print(f"Alembic version: {version[0] if version else 'None'}")
        
        # Check users table columns
        inspector = inspect(db.get_bind())
        columns = inspector.get_columns('users')
        
        print("\nUsers table columns:")
        for column in columns:
            print(f"  - {column['name']}: {column['type']}")
        
        # Check if role column exists
        role_column = next((c for c in columns if c['name'] == 'role'), None)
        if role_column:
            print(f"\n✅ Role column found: {role_column['type']}")
            print(f"   Nullable: {role_column['nullable']}")
            print(f"   Default: {role_column.get('default', 'None')}")
        else:
            print("\n❌ Role column NOT found!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_migration()