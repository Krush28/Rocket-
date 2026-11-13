"""offline gazetteer (places) + name translations

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("places",
                    sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("key", sa.String(160), nullable=False),
                    sa.Column("name", sa.String(160), nullable=False),
                    sa.Column("name_dev", sa.String(160)),
                    sa.Column("admin1", sa.String(80), nullable=False, server_default=""),
                    sa.Column("admin2", sa.String(120), nullable=False, server_default=""),
                    sa.Column("lat", sa.Float(), nullable=False),
                    sa.Column("lon", sa.Float(), nullable=False),
                    sa.Column("population", sa.Integer(), nullable=False, server_default="0"),
                    sa.Column("kind", sa.String(8), nullable=False))
    op.create_index("ix_places_key", "places", ["key"])
    op.create_table("name_translations",
                    sa.Column("src", sa.String(200), primary_key=True),
                    sa.Column("dev", sa.String(200), nullable=False))


def downgrade():
    op.drop_table("name_translations")
    op.drop_index("ix_places_key", "places")
    op.drop_table("places")
