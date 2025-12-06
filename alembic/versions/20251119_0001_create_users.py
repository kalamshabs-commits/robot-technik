from alembic import op
import sqlalchemy as sa

revision = '20251119_0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_enc', sa.String(), nullable=False),
        sa.Column('serial_enc', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

def downgrade():
    op.drop_table('users')