"""forecast cache (full backtested forecasts computed in the background)

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("forecast_cache",
                    sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("crop", sa.String(160), nullable=False),
                    sa.Column("mandi", sa.String(300), nullable=False),
                    sa.Column("last_date", sa.Date(), nullable=False),
                    sa.Column("version", sa.String(20), nullable=False),
                    sa.Column("payload", sa.JSON(), nullable=False),
                    sa.UniqueConstraint("crop", "mandi", "last_date", "version"))


def downgrade():
    op.drop_table("forecast_cache")
