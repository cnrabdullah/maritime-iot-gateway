from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Union, Optional

@dataclass
class SensorReading:
    sensor_id: str
    value: Union[float, int, None]
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "Valid"
    mqtt_topic_suffix: Optional[str] = None
    change_threshold: Optional[float] = None
    min_publish_interval_seconds: Optional[int] = None