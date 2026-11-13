"""Load the offline India gazetteer (GeoNames IN.txt + admin codes + postal/IN.txt) into `places`. Safe to rerun (replaces).
Get the files (~30 MB zipped, not in git):  https://download.geonames.org/export/dump/{IN.zip,admin1CodesASCII.txt,admin2Codes.txt}
and https://download.geonames.org/export/zip/IN.zip (unzip into <dir>/postal/).
Run: MSYS_NO_PATHCONV=1 docker compose run --rm backend python scripts/load_gazetteer.py /data/raw/geonames"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal  # noqa: E402
from app.services import gazetteer  # noqa: E402

if __name__ == "__main__":
    t = time.time()
    with SessionLocal() as s:
        print({"rows": gazetteer.load(s, sys.argv[1] if len(sys.argv) > 1 else "/data/raw/geonames"), "seconds": round(time.time() - t)}, flush=True)
