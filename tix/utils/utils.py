from datetime import datetime

def get_date(date_str):
    """Parse a date string in ISO or common formats. Returns ISO string or None if invalid."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat()
        except Exception:
            continue
    # Try parsing as ISO format
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.isoformat()
    except Exception:
        return None
