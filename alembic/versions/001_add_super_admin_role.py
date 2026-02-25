"""add super_admin role

Revision ID: 001
Revises:
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 super_admin 到 userrole 枚举类型
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin'")


def downgrade() -> None:
    # PostgreSQL 不支持直接删除枚举值，需要重建枚举类型
    # 这里留空，因为删除枚举值比较复杂且风险较高
    pass
