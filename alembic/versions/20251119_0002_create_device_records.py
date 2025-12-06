from alembic import op
import sqlalchemy as sa

revision = '20251119_0002'
down_revision = '20251119_0001'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'device_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_enc', sa.String(), nullable=True),
        sa.Column('phone_enc', sa.String(), nullable=True),
        sa.Column('serial_enc', sa.String(), nullable=True),
        sa.Column('device_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

def downgrade():
    op.drop_table('device_records')