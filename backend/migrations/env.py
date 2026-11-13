from alembic import context

import app.models  # noqa: F401  registers every table on Base.metadata
from app.core.config import settings
from app.db.database import Base, make_engine

cfg = context.config
url = cfg.attributes.get("url") or context.get_x_argument(as_dictionary=True).get("url") or settings.database_url


def run():
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    with make_engine(url).connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata, render_as_batch=conn.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()


run()
