# alembic/versions/002_add_conversations.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String, default='New Conversation'),
        sa.Column('messages', sa.JSON, default=[]),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )
    
    # Create messages table (alternative approach if you prefer separate table)
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('conversation_id', sa.Integer, sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String, nullable=False),
        sa.Column('content', sa.String, nullable=False),
        sa.Column('intermediate_steps', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('messages')
    op.drop_table('conversations')