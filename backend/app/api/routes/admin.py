import hmac
import os
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException

from app.ml import forecast as F
from app.schemas.chat import ImportIn
from app.services.adapters import agmarknet_datagov as adapters

router = APIRouter(prefix="/admin", tags=["admin"])


def data_raw() -> Path:
    env = os.getenv("KRISHIX_DATA_RAW")
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[4] / "data" / "raw"
    return repo if repo.is_dir() else Path("/data/raw")


def _auth(token: str | None):
    """shortcut: one shared ADMIN_TOKEN until Phase 8 adds user auth + RBAC. Unset token = admin API disabled."""
    want = os.getenv("ADMIN_TOKEN")
    if not want or not token or not hmac.compare_digest(want, token):
        raise HTTPException(403, "admin token required")


@router.post("/import")
def import_csv(b: ImportIn, x_admin_token: str | None = Header(default=None)):
    """Import a data.gov.in price CSV that sits under data/raw/ (no other paths are readable)."""
    _auth(x_admin_token)
    root = data_raw().resolve()
    p = (root / b.path).resolve()
    if not p.is_relative_to(root) or p.suffix.lower() != ".csv":
        raise HTTPException(400, "path must be a .csv file inside data/raw/")
    if not p.is_file():
        raise HTTPException(404, "file not found in data/raw/")
    try:
        rep = adapters.import_csv(str(p))
    except ValueError as e:
        raise HTTPException(422, str(e))
    F.forecast.cache_clear()
    return rep


@router.post("/refresh")
def refresh(x_admin_token: str | None = Header(default=None)):
    """Pull today's prices from the data.gov.in API (needs DATA_GOV_API_KEY)."""
    _auth(x_admin_token)
    if not adapters.api_key():
        raise HTTPException(400, "DATA_GOV_API_KEY is not set")
    F.forecast.cache_clear()
    return adapters.refresh()
