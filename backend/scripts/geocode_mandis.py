"""One-off / resumable job: geocode every pending mandi (about 1 request per second; safe to stop and rerun).
Run: docker compose run --rm backend python scripts/geocode_mandis.py [limit]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal  # noqa: E402
from app.services.geocoding import geocode_mandis  # noqa: E402

if __name__ == "__main__":
    with SessionLocal() as s:
        print(geocode_mandis(s, int(sys.argv[1]) if len(sys.argv) > 1 else None), flush=True)
