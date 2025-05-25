from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional, Union

class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: str = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

class ModbusCollectorConfig(BaseModel):
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8889
    default_unit_id: int = 1
    default_polling_interval_seconds: float = Field(0.5, gt=0)
    default_read_timeout_seconds: float = Field(0.1, gt=0)
    connection_retry_delay_seconds: int = Field(5, ge=1)

class NmeaCollectorConfig(BaseModel):
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8888
    connection_retry_delay_seconds: int = Field(5, ge=1)

class CollectorsConfig(BaseModel):
    modbus_collector: ModbusCollectorConfig = Field(default_factory=ModbusCollectorConfig)
    nmea_collector: NmeaCollectorConfig = Field(default_factory=NmeaCollectorConfig)

class SensorModbusCollectorParams(BaseModel):
    register_address: int = Field(..., ge=0)
    unit_id: Optional[int] = None
    polling_interval_seconds: Optional[float] = None

class SensorNmeaCollectorParams(BaseModel):
    expected_talker_id: str
    expected_sentence_type: str

class SensorPublisherParams(BaseModel):
    mqtt_topic_suffix: str
    unit: str
    change_threshold: float
    min_publish_interval_seconds: Optional[int] = None

class SensorConfig(BaseModel):
    id: str
    name: str
    collector_type: Literal["modbus_tcp", "nmea"]
    collector_config: Union[SensorModbusCollectorParams, SensorNmeaCollectorParams]
    publisher_config: SensorPublisherParams

    @field_validator('collector_config', mode='before')
    @classmethod
    def _check_collector_config_type(cls, v: any, values: any) -> any:
        return v

class MqttPublisherConfig(BaseModel):
    enabled: bool = True
    broker_host: str = "broker.hivemq.com"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id_prefix: str = "ows-challenge"
    keepalive_seconds: int = Field(600, ge=60)
    default_min_publish_interval_seconds: int = Field(300, ge=1)
    lwt_message: str = "connection lost"
    topic_prefix: str = "ows-challenge/mv-sinking-boat"
    timestamp_format: str = "%Y-%m-%d at %H:%M UTC"

class AppConfig(BaseModel):
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    application_name: str = "MaritimeIoTGateway"
    collectors: CollectorsConfig = Field(default_factory=CollectorsConfig)
    sensors: List[SensorConfig] = []
    mqtt_publisher: MqttPublisherConfig = Field(default_factory=MqttPublisherConfig)