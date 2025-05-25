import datetime
import logging

logger = logging.getLogger(__name__)
def format_payload_timestamp(dt: datetime.datetime, fmt: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime(fmt)