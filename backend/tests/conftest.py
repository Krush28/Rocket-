import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db import database
from app.ml import forecast
from app.repositories import market_data as MD


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    """Every test gets an empty SQLite DB (so DEMO mode unless the test loads live rows). Never touches the real database."""
    eng = database.make_engine(f"sqlite:///{tmp_path}/test.db")
    database.Base.metadata.create_all(eng)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=eng, autoflush=False, expire_on_commit=False))
    for k, v in {"FORECAST_BACKGROUND": "0", "MANDI_API_JOB": "0", "KRISHIX_HYBRID_HISTORY": "0", "KRISHIMITRA_LLM": ""}.items():
        monkeypatch.setenv(k, v)  # no threads, no network, no LLM; hybrid history is opt-in per test
    forecast.forecast.cache_clear()
    MD.clear()
    with database.SessionLocal() as s:
        yield s
    forecast.forecast.cache_clear()
    MD.clear()
    eng.dispose()
