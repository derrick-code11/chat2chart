from datetime import datetime


def iso_z(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    s = dt.isoformat()
    if s.endswith("+00:00"):
        return s.replace("+00:00", "Z")
    return s
