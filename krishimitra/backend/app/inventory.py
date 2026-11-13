"""Remembers a farmer's crops and farm details between visits, keyed by a random device id the browser keeps (no accounts, no Aadhaar).
farmer = {"location", "ready", "can_store", "lang", "lots": {crop: {"qty_kg", "original_qty", "original_unit"}}}"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "farmer.db"


def _c():
    c = sqlite3.connect(DB)
    c.execute("create table if not exists farmer(device text primary key, data text, updated text)")
    return c


def save(device: str, data: dict) -> None:
    with _c() as c:
        c.execute("insert or replace into farmer values(?,?,?)", (device, json.dumps(data), datetime.now(timezone.utc).isoformat()))


def load(device: str) -> dict | None:
    if not DB.exists():
        return None
    with _c() as c:
        r = c.execute("select data from farmer where device=?", (device,)).fetchone()
    return json.loads(r[0]) if r else None


def clear(device: str) -> None:
    if DB.exists():
        with _c() as c:
            c.execute("delete from farmer where device=?", (device,))
