import math


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(d))


def road_km(a, b, factor=1.3):
    """Estimate (straight-line x factor), not routed distance. Swap for OSRM when available."""
    return haversine_km(a, b) * factor
