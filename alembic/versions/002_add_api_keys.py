from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('key_hash', sa.String(128), nullable=False, unique=True),
        sa.Column('permissions', sa.Text, default='["chat"]'),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    
    # Create indexes
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_tenant_id', 'api_keys', ['tenant_id'])
    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'])
    
    # Check if conversations table needs updating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'conversations' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('conversations')]
        
        # Add conversation_metadata instead of metadata
        if 'conversation_metadata' not in columns:
            op.add_column('conversations', sa.Column('conversation_metadata', sa.JSON, default={}))
        
        # Remove metadata if it exists (rename or drop)
        if 'metadata' in columns:
            # Option 1: Drop the column if it exists and isn't used
            op.drop_column('conversations', 'metadata')
        
        # Add other columns if needed
        if 'is_archived' not in columns:
            op.add_column('conversations', sa.Column('is_archived', sa.Boolean, default=False))
        if 'is_pinned' not in columns:
            op.add_column('conversations', sa.Column('is_pinned', sa.Boolean, default=False))

def downgrade():
    op.drop_table('api_keys')
    
    # Revert conversation changes if needed
    op.drop_column('conversations', 'conversation_metadata')
    op.drop_column('conversations', 'is_archived')
    op.drop_column('conversations', 'is_pinned')
    
    # Optionally restore metadata column
    op.add_column('conversations', sa.Column('metadata', sa.JSON, default={}))