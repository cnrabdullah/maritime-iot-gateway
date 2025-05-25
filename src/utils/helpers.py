import datetime
import logging

logger = logging.getLogger(__name__)

def generate_mqtt_client_id(prefix: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    date_str = now.strftime("%d%m%y")
    client_id = f"{prefix}-{date_str}"
    return client_id

def format_payload_timestamp(dt: datetime.datetime, fmt: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime(fmt)