import asyncio
import logging
import pynmea2
from datetime import datetime, timezone
from typing import Optional, Dict

from ..models.config_models import SensorConfig, SensorNmeaCollectorParams, NmeaCollectorConfig
from ..models.sensor_reading import SensorReading

logger = logging.getLogger(__name__)

class NmeaCollector:
    def __init__(self, collector_config: NmeaCollectorConfig):
        self.config = collector_config
        self._sensor_configs: Dict[str, SensorConfig] = {}
        self._data_queue: Optional[asyncio.Queue] = None
        self._connection_task: Optional[asyncio.Task] = None
        self._running = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def _process_line(self, raw_line: str):
        if not self._data_queue: return

        try:
            clean_line = raw_line.strip()
            if not clean_line: return

            nmea_msg = pynmea2.parse(clean_line)
            
            for sensor_id, sensor_cfg in self._sensor_configs.items():
                if not isinstance(sensor_cfg.collector_config, SensorNmeaCollectorParams): continue
                nmea_params = sensor_cfg.collector_config
                
                if (nmea_msg.talker == nmea_params.expected_talker_id and
                    nmea_msg.sentence_type == nmea_params.expected_sentence_type):
                    
                    value = None
                    status = "Invalid" 

                    if nmea_msg.sentence_type == 'ROT':
                        if len(nmea_msg.data) >= 2:
                            rot_str, data_status_char = nmea_msg.data[0], nmea_msg.data[1]
                            if data_status_char == 'A':
                                try: value = float(rot_str); status = "Valid"
                                except ValueError: logger.error(f"NMEA: Bad ROT value '{rot_str}'")

                    reading = SensorReading(
                        sensor_id=sensor_id, value=value, unit=sensor_cfg.publisher_config.unit, status=status,
                        timestamp=datetime.now(timezone.utc), mqtt_topic_suffix=sensor_cfg.publisher_config.mqtt_topic_suffix,
                        change_threshold=sensor_cfg.publisher_config.change_threshold,
                        min_publish_interval_seconds=sensor_cfg.publisher_config.min_publish_interval_seconds
                    )
                    await self._data_queue.put(reading)
                    return 
        except pynmea2.ParseError:
            logger.warning(f"NMEA: Parse Error. Raw: '{raw_line.strip()}'")
        except Exception as e:
            logger.error(f"NMEA: Error processing line '{raw_line.strip()}': {e}")

    async def _connection_loop(self):
        logger.info(f"NMEA: Connecting to TCP {self.config.host}:{self.config.port}")
        while self._running:
            try:
                self._reader, self._writer = await asyncio.open_connection(self.config.host, self.config.port)
                logger.info(f"NMEA: Connected to TCP server: {self.config.host}:{self.config.port}")
                while self._running:
                    line_bytes = await self._reader.readline()
                    if not line_bytes: logger.warning("NMEA: Server closed connection."); break 
                    await self._process_line(line_bytes.decode('ascii', errors='ignore'))
            except Exception as e:
                logger.error(f"NMEA: Connection/read error: {e}. Retrying in {self.config.connection_retry_delay_seconds}s...")
            finally:
                if self._writer and not self._writer.is_closing():
                    self._writer.close()
                    try: await self._writer.wait_closed()
                    except Exception: pass
                self._reader, self._writer = None, None
            if not self._running: break
            await asyncio.sleep(self.config.connection_retry_delay_seconds)
        logger.info("NMEA: Connection loop stopped.")

    async def start(self, sensors_to_collect: list[SensorConfig], data_queue: asyncio.Queue):
        if not self.config.enabled: return
        self._running = True
        self._data_queue = data_queue
        for sensor_cfg in sensors_to_collect:
            if sensor_cfg.collector_type == "nmea":
                if isinstance(sensor_cfg.collector_config, SensorNmeaCollectorParams):
                    self._sensor_configs[sensor_cfg.id] = sensor_cfg
        if not self._sensor_configs: logger.info("NMEA: No sensors for this collector."); self._running=False; return
        self._connection_task = asyncio.create_task(self._connection_loop())

    async def stop(self):
        self._running = False
        if self._writer and not self._writer.is_closing():
            self._writer.close(); await asyncio.sleep(0.1)
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            try: await self._connection_task
            except asyncio.CancelledError: pass
        logger.info("NMEA TCP Collector stopped.")