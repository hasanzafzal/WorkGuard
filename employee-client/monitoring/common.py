"""
common.py

Shared helper for building events that conform to the standard event schema
used by every monitoring component:

    {
        "event_id": "...",
        "event_type": "...",
        "source": "...",
        "timestamp": "ISO-8601",
        "data": {...}
    }
"""

import uuid
from datetime import datetime, timezone


def make_event(event_type: str, source: str, data: dict) -> dict:
    """Build a single event following the common schema."""
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "source": source,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "data": data,
    }
