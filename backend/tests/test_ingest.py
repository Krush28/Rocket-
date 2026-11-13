from sqlalchemy import func, select

from app.db import database
from app.models import Commodity, Mandi, MandiPrice
from app.services.adapters import agmarknet_datagov as adapters

HEADER = "State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_x0020_Price,Max_x0020_Price,Modal_x0020_Price\n"
ROWS = ("Goa,North Goa,Mapusa APMC,Tomato,Local,FAQ,13/11/2026,1200,1600,1400\n"
        "Goa,South Goa,Margao APMC,Tomato,Local,FAQ,13/11/2026,1300,1700,1500\n"
        "Goa,South Goa,Margao APMC,Onion,Red,FAQ,13/11/2026,NA,NA,NA\n"
        "Goa,South Goa,Margao APMC,Potato,Local,FAQ,13/11/2026,0,0,0\n")


def _csv(tmp_path):
    f = tmp_path / "9ef84268-test.csv"
    f.write_text(HEADER + ROWS)
    return str(f)


def _count(model):
    with database.SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(model))


def test_import_counts_and_skips(tmp_path):
    r = adapters.import_csv(_csv(tmp_path))
    assert (r["rows_read"], r["rows_upserted"], r["rows_skipped"]) == (4, 2, 2)
    assert _count(Mandi) == 2


def test_reimport_is_idempotent(tmp_path):
    f = _csv(tmp_path)
    adapters.import_csv(f)
    adapters.import_csv(f)
    assert _count(MandiPrice) == 2


def test_rows_are_official_with_source(tmp_path):
    adapters.import_csv(_csv(tmp_path))
    with database.SessionLocal() as s:
        p = s.scalars(select(MandiPrice)).first()
        assert p.verification_status == "official" and p.source_id is not None and p.unit == "Rs/quintal"
        assert s.scalar(select(Commodity.key).where(Commodity.name == "Tomato")) == "tomato"
