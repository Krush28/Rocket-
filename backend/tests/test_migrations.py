from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

INI = Path(__file__).resolve().parents[1] / "alembic.ini"
TABLES = {"mandis", "mandi_prices", "farmer_inventory", "farmer_profiles", "conversation_sessions", "geocode_cache",
          "users", "commodities", "crop_varieties", "data_sources", "audit_logs"}


def _cfg(url):
    c = Config(str(INI))
    c.attributes["url"] = url
    return c


def test_upgrade_and_downgrade_on_sqlite(tmp_path):
    url = f"sqlite:///{tmp_path}/t.db"
    command.upgrade(_cfg(url), "head")
    assert TABLES <= set(inspect(create_engine(url)).get_table_names())
    command.downgrade(_cfg(url), "base")
    assert not TABLES & set(inspect(create_engine(url)).get_table_names())
