"""end-to-end operations: sale orders, transport jobs, warehouses, storage bookings, notifications; user login token

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _ts():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now())]


def upgrade():
    with op.batch_alter_table("users") as b:  # batch: works on SQLite (tests) and Postgres
        b.add_column(sa.Column("token", sa.String(64)))
        b.add_column(sa.Column("state", sa.String(80)))
        b.create_index("ix_users_token", ["token"], unique=True)
    op.create_table("sale_orders", sa.Column("id", sa.String(20), primary_key=True), sa.Column("device", sa.String(100), nullable=False, index=True),
                    sa.Column("crop", sa.String(160), nullable=False), sa.Column("qty_kg", sa.Float(), nullable=False),
                    sa.Column("destination", sa.String(300), nullable=False), sa.Column("status", sa.String(40), nullable=False),
                    sa.Column("payload", sa.JSON(), nullable=False), sa.Column("log", sa.JSON(), nullable=False), *_ts())
    op.create_table("transport_jobs", sa.Column("id", sa.String(20), primary_key=True),
                    sa.Column("order_id", sa.String(20), sa.ForeignKey("sale_orders.id"), nullable=False, index=True),
                    sa.Column("status", sa.String(30), nullable=False), sa.Column("pickup", sa.JSON(), nullable=False), sa.Column("drop", sa.JSON(), nullable=False),
                    sa.Column("crop", sa.String(160), nullable=False), sa.Column("qty_kg", sa.Float(), nullable=False), sa.Column("vehicle", sa.String(40)),
                    sa.Column("distance_km", sa.Float()), sa.Column("est_fare", sa.Float()), sa.Column("transporter_id", sa.Integer(), sa.ForeignKey("users.id")),
                    sa.Column("transporter_name", sa.String(120)), sa.Column("log", sa.JSON(), nullable=False), *_ts())
    op.create_table("warehouses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(20), unique=True, nullable=False),
                    sa.Column("name", sa.String(160), nullable=False), sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id")),
                    sa.Column("kind", sa.String(20), nullable=False), sa.Column("temp", sa.String(30), nullable=False),
                    sa.Column("district", sa.String(120), nullable=False), sa.Column("state", sa.String(80), nullable=False, index=True),
                    sa.Column("lat", sa.Float(), nullable=False), sa.Column("lon", sa.Float(), nullable=False),
                    sa.Column("capacity_qtl", sa.Float(), nullable=False), sa.Column("free_qtl", sa.Float(), nullable=False),
                    sa.Column("rate_qtl_day", sa.Float(), nullable=False), sa.Column("min_days", sa.Integer(), nullable=False),
                    sa.Column("handling_qtl", sa.Float(), nullable=False), sa.Column("categories", sa.JSON(), nullable=False),
                    sa.Column("verification", sa.String(20), nullable=False), *_ts())
    op.create_table("storage_bookings", sa.Column("id", sa.String(20), primary_key=True), sa.Column("device", sa.String(100), nullable=False, index=True),
                    sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False, index=True),
                    sa.Column("crop", sa.String(160), nullable=False), sa.Column("qty_kg", sa.Float(), nullable=False), sa.Column("days", sa.Integer(), nullable=False),
                    sa.Column("est_cost", sa.Float(), nullable=False), sa.Column("status", sa.String(20), nullable=False),
                    sa.Column("payload", sa.JSON(), nullable=False), sa.Column("log", sa.JSON(), nullable=False), *_ts())
    op.create_table("notifications", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("audience", sa.String(140), nullable=False, index=True),
                    sa.Column("title", sa.String(200), nullable=False), sa.Column("body", sa.String(600), nullable=False), sa.Column("link", sa.String(200)),
                    sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
                    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade():
    for t in ("notifications", "storage_bookings", "warehouses", "transport_jobs", "sale_orders"):
        op.drop_table(t)
    with op.batch_alter_table("users") as b:
        b.drop_index("ix_users_token")
        b.drop_column("state")
        b.drop_column("token")
