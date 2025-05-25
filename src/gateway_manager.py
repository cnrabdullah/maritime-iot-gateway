import asyncio
import logging
from typing import List, Optional

from .models.config_models import AppConfig
from .models.sensor_reading import SensorReading
from .collectors.modbus_collector import ModbusCollector
from .collectors.nmea_collector import NmeaCollector
from .publishers.mqtt_publisher import MQTTPublisher

logger = logging.getLogger(__name__)

class GatewayManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_queue: asyncio.Queue[SensorReading] = asyncio.Queue()
        
        self.modbus_collector: Optional[ModbusCollector] = None
        if config.collectors.modbus_collector.enabled:
            if any(s.collector_type == "modbus_tcp" for s in config.sensors):
                self.modbus_collector = ModbusCollector(config.collectors.modbus_collector)

        self.nmea_collector: Optional[NmeaCollector] = None
        if config.collectors.nmea_collector.enabled:
            if any(s.collector_type == "nmea" for s in config.sensors):
                self.nmea_collector = NmeaCollector(config.collectors.nmea_collector)

        self.mqtt_publisher: Optional[MQTTPublisher] = None
        if config.mqtt_publisher.enabled:
            self.mqtt_publisher = MQTTPublisher(config.mqtt_publisher)
            
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None

    async def _process_data_queue(self):
        while self._running:
            try:
                reading = await self.data_queue.get()
                if self.mqtt_publisher:
                    await self.mqtt_publisher.publish_reading(reading)
                self.data_queue.task_done()
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Queue processing error: {e}")

    async def start(self):
        logger.info("Starting GatewayManager...")
        self._running = True

        if self.mqtt_publisher: await self.mqtt_publisher.start(); await asyncio.sleep(1)

        collectors_to_start = []
        if self.modbus_collector: collectors_to_start.append(self.modbus_collector.start(self.config.sensors, self.data_queue))
        if self.nmea_collector: collectors_to_start.append(self.nmea_collector.start(self.config.sensors, self.data_queue))
        if collectors_to_start: await asyncio.gather(*collectors_to_start)

        self._processing_task = asyncio.create_task(self._process_data_queue())
        logger.info("GatewayManager running.")
        while self._running: await asyncio.sleep(1)

    async def stop(self):
        logger.info("Stopping GatewayManager...")
        self._running = False 

        stoppers = []
        if self.modbus_collector: stoppers.append(self.modbus_collector.stop())
        if self.nmea_collector: stoppers.append(self.nmea_collector.stop())
        if stoppers: await asyncio.gather(*stoppers, return_exceptions=True)

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try: await self._processing_task
            except asyncio.CancelledError: pass
        
        if self.mqtt_publisher: await self.mqtt_publisher.stop()
        logger.info("GatewayManager stopped.")