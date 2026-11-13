"""state-average price history (Mandi API)

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("state_price_history",
                    sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("state", sa.String(80), nullable=False),
                    sa.Column("commodity_key", sa.String(160), nullable=False),
                    sa.Column("price_date", sa.Date(), nullable=False),
                    sa.Column("avg_modal", sa.Float(), nullable=False),
                    sa.Column("avg_min", sa.Float()),
                    sa.Column("avg_max", sa.Float()),
                    sa.Column("data_points", sa.Integer(), nullable=False, server_default="0"),
                    sa.UniqueConstraint("state", "commodity_key", "price_date"))


def downgrade():
    op.drop_table("state_price_history")
