"""add view_count to collections

Revision ID: 004
Revises: 003
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 view_count 字段
    op.add_column('collections', sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    # 删除 view_count 字段
    op.drop_column('collections', 'view_count')
