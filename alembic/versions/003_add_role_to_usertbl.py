"""Add role column to users table with enum

Revision ID: xxxx
Revises: previous_revision_id
Create Date: 2024-03-24 12:34:56.789012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if users table exists (it should)
    if 'users' not in inspector.get_table_names():
        print("Users table doesn't exist, skipping migration")
        return
    
    # Check if role column already exists
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'role' not in columns:
        print("Adding role column to users table...")
        
        # Check if enum type exists
        if conn.dialect.name == 'postgresql':
            result = conn.execute("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole')")
            enum_exists = result.scalar()
            
            if not enum_exists:
                # Create enum type
                op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user', 'viewer')")
                print("Created userrole enum type")
        
        # Add column as nullable first
        op.add_column('users', 
            sa.Column('role', 
                sa.Enum('admin', 'user', 'viewer', name='userrole') if conn.dialect.name == 'postgresql' else sa.String(50),
                nullable=True
            )
        )
        
        # Set default role for existing users
        print("Setting default role for existing users...")
        op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
        
        # Make it NOT NULL
        op.alter_column('users', 'role',
            nullable=False,
            server_default='user'
        )
        
        # Add index
        op.create_index('ix_users_role', 'users', ['role'])
        print("Successfully added role column")
    else:
        print("Role column already exists, skipping migration")

def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if column exists
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'role' in columns:
            print("Removing role column...")
            
            # Drop index
            op.drop_index('ix_users_role', table_name='users')
            
            # Drop column
            op.drop_column('users', 'role')
            print("Removed role column")
    
    # Drop enum type (only if PostgreSQL)
    if conn.dialect.name == 'postgresql':
        result = conn.execute("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole')")
        enum_exists = result.scalar()
        
        if enum_exists:
            op.execute("DROP TYPE userrole")
            print("Dropped userrole enum type")