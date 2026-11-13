"""Common metadata block every agent returns (source, freshness, verification, uncertainty, error)."""
from datetime import datetime, timezone


def meta(source, verification, *, updated=None, confidence=None, error=None, note=None):
    now = datetime.now(timezone.utc)
    updated = updated or now
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return {
        "source": source,
        "verification": verification,  # verified | unverified | demo | estimate
        "observed_at": now.isoformat(),
        "last_updated": updated.isoformat(),
        "freshness_days": round((now - updated).total_seconds() / 86400, 1),
        "confidence": confidence,
        "error": error,
        "note": note,
    }
