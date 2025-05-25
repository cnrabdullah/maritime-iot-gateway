import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional
import paho.mqtt.client as mqtt

from ..models.config_models import MqttPublisherConfig
from ..models.sensor_reading import SensorReading
from ..utils.helpers import generate_mqtt_client_id, format_payload_timestamp

logger = logging.getLogger(__name__)

class MQTTPublisher:
    def __init__(self, publisher_config: MqttPublisherConfig):
        self.config = publisher_config
        self.client_id = generate_mqtt_client_id(self.config.client_id_prefix)
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self._last_published_data: Dict[str, Tuple[Optional[float], datetime]] = {}
        self._connected = False
        self._running = False
        self._setup_client()

    def _setup_client(self):
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        if self.config.username and self.config.password:
            self.client.username_pw_set(self.config.username, self.config.password)
        
        lwt_topic = f"{self.config.topic_prefix}/gateway_status"
        self.client.will_set(lwt_topic, payload=self.config.lwt_message, qos=1, retain=True)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0: self._connected = True; logger.info(f"MQTT: Connected to {self.config.broker_host}")
        else: self._connected = False; logger.error(f"MQTT: Connection failed: {mqtt.connack_string(rc)}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self._connected = False; logger.warning(f"MQTT: Disconnected. Will auto-reconnect: {rc}")

    async def start(self):
        if not self.config.enabled: return
        self._running = True
        try:
            self.client.connect(self.config.broker_host, self.config.broker_port, self.config.keepalive_seconds)
            self.client.loop_start()
            logger.info("MQTT Publisher started.")
        except Exception as e:
            logger.error(f"MQTT: Initial connection error: {e}. Will retry in background.")

    async def stop(self):
        self._running = False
        if self.client:
            lwt_topic = f"{self.config.topic_prefix}/gateway_status"
            self.client.publish(lwt_topic, "offline_graceful", qos=1, retain=True)
            await asyncio.sleep(0.1)
            self.client.loop_stop(); self.client.disconnect()
        logger.info("MQTT Publisher stopped.")

    async def publish_reading(self, reading: SensorReading):
        if not self.config.enabled or not self._running or not self._connected: return
        if reading.mqtt_topic_suffix is None: return

        full_topic = f"{self.config.topic_prefix}/{reading.mqtt_topic_suffix}"
        last_val, last_pub_time = self._last_published_data.get(reading.sensor_id, (None, datetime.min.replace(tzinfo=timezone.utc)))
        
        changed = False
        if reading.value is not None and reading.status == "Valid":
            if last_val is None or abs(reading.value - last_val) > (reading.change_threshold or 0.0):
                changed = True
        elif reading.status != "Valid" and last_val is not None :
             changed = True

        interval_reached = (datetime.now(timezone.utc) - last_pub_time) >= timedelta(seconds=reading.min_publish_interval_seconds or self.config.default_min_publish_interval_seconds)
        first_message = reading.sensor_id not in self._last_published_data

        if changed or interval_reached or first_message:
            val_str = f"{reading.value:.1f}{reading.unit}" if reading.value is not None else "N/A"
            status_str = "Valid" if reading.status == "Valid" and reading.value is not None else "Invalid"
            
            timestamp_str = format_payload_timestamp(reading.timestamp, self.config.timestamp_format)
            payload = f"{val_str}, {status_str}, {timestamp_str}"
            
            msg_info = self.client.publish(topic=full_topic, payload=payload, qos=1, retain=False)
            if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
                self._last_published_data[reading.sensor_id] = (reading.value, datetime.now(timezone.utc))

    def is_connected(self) -> bool: return self._connected