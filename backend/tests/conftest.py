import pytest
from app.services.adapters import agmarknet_datagov as adapters
from app.ml import forecast


@pytest.fixture(autouse=True)
def _isolate_live_db(tmp_path, monkeypatch):
    """Tests run in DEMO mode unless a test loads its own live rows; never touch the real live_prices.db."""
    monkeypatch.setattr(adapters, "DB", tmp_path / "isolated.db")
    forecast.forecast.cache_clear()
    yield
    forecast.forecast.cache_clear()
