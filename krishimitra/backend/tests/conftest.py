import pytest
from app import adapters, agent, forecast, intake, inventory, profile


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """DEMO mode, empty stores, no leftover conversations: tests never touch live_prices.db, farmer.db or earlier sessions."""
    monkeypatch.setattr(adapters, "DB", tmp_path / "isolated.db")
    monkeypatch.setattr(inventory, "DB", tmp_path / "farmer.db")
    for store in (agent.STATE, intake.S, profile.SESSIONS):
        store.clear()
    forecast.forecast.cache_clear()
    yield
    forecast.forecast.cache_clear()
