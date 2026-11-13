"""7-day weather for the farm from Open-Meteo (free, no key; only the village coordinates are sent) + selling advice.
Advice is rule-based and conservative: rain -> cover produce and avoid open trucks that day; heat -> move perishables early;
otherwise a good window for harvest and transport. Cached 1 hour per location; on any failure returns None (UI hides the card)."""
import time

import httpx

URL = "https://api.open-meteo.com/v1/forecast"
_cache: dict = {}


def kind(code: int) -> str:
    """WMO weather code -> clear | partly | cloudy | fog | drizzle | rain | storm."""
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 57:
        return "drizzle"
    if 61 <= code <= 67 or 80 <= code <= 82 or 71 <= code <= 77 or 85 <= code <= 86:
        return "rain"
    if code >= 95:
        return "storm"
    return "cloudy"


def advice(days: list[dict]) -> list[dict]:
    out = []
    wet = [d for d in days[:3] if d["rain_pct"] >= 60 or d["rain_mm"] >= 5 or d["kind"] in ("rain", "storm")]
    if wet:
        out.append({"key": "rain", "day": wet[0]["date"]})
    if any(d["tmax"] >= 38 for d in days[:3]):
        out.append({"key": "heat"})
    if any(d["wind"] >= 40 for d in days[:3]):
        out.append({"key": "wind"})
    if not out:
        out.append({"key": "clear"})
    return out


def forecast(lat: float, lon: float) -> dict | None:
    key = (round(lat, 2), round(lon, 2))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    try:
        r = httpx.get(URL, timeout=8, params={
            "latitude": lat, "longitude": lon, "timezone": "Asia/Kolkata", "forecast_days": 7,
            "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"})
        d = r.json()
        c, dl = d["current"], d["daily"]
        days = [{"date": dl["time"][i], "kind": kind(int(dl["weather_code"][i])), "tmax": round(dl["temperature_2m_max"][i]),
                 "tmin": round(dl["temperature_2m_min"][i]), "rain_mm": round(dl["precipitation_sum"][i] or 0, 1),
                 "rain_pct": int(dl["precipitation_probability_max"][i] or 0), "wind": round(dl["wind_speed_10m_max"][i] or 0)}
                for i in range(len(dl["time"]))]
        out = {"current": {"temp": round(c["temperature_2m"]), "kind": kind(int(c["weather_code"])), "humidity": c.get("relative_humidity_2m"),
                           "wind": round(c.get("wind_speed_10m") or 0)}, "days": days, "advice": advice(days), "source": "Open-Meteo"}
    except Exception:
        return None
    _cache[key] = (time.time(), out)
    return out
