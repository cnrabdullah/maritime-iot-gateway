import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
from datetime import datetime, timezone

from ..models.config_models import ModbusCollectorConfig, SensorConfig, SensorModbusCollectorParams
from ..models.sensor_reading import SensorReading

logger = logging.getLogger(__name__)

class ModbusCollector:
    def __init__(self, collector_config: ModbusCollectorConfig):
        self.config = collector_config
        self.client = AsyncModbusTcpClient(host=self.config.host, port=self.config.port, timeout=self.config.default_read_timeout_seconds)
        self._sensor_tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def _connect_client(self):
        while self._running and not self.client.connected:
            try:
                logger.info(f"Attempting to connect to Modbus server at {self.config.host}:{self.config.port}")
                await self.client.connect()
                if self.client.connected:
                    logger.info(f"Successfully connected to Modbus server at {self.config.host}:{self.config.port}")
                    break
            except Exception as e:
                logger.error(f"Failed to connect to Modbus server: {e}. Retrying in {self.config.connection_retry_delay_seconds}s...")
                await asyncio.sleep(self.config.connection_retry_delay_seconds)
            if not self._running:
                break

    async def _read_sensor_loop(self, sensor: SensorConfig, data_queue: asyncio.Queue):
        if not isinstance(sensor.collector_config, SensorModbusCollectorParams):
            logger.error(f"Invalid collector_config type for Modbus sensor {sensor.id}")
            return

        sensor_modbus_params = sensor.collector_config
        unit_id = sensor_modbus_params.unit_id or self.config.default_unit_id
        polling_interval = sensor_modbus_params.polling_interval_seconds or self.config.default_polling_interval_seconds
        register_address = sensor_modbus_params.register_address
        
        logger.info(f"Starting Modbus polling for sensor {sensor.id} (Register: {register_address}, Unit: {unit_id}) every {polling_interval}s")

        while self._running:
            try:
                if not self.client.connected:
                    logger.warning(f"Modbus client disconnected for sensor {sensor.id}. Attempting to reconnect...")
                    await self._connect_client()
                    if not self.client.connected:
                        logger.error(f"Modbus reconnection failed for sensor {sensor.id}. Sleeping before next attempt.")
                        await asyncio.sleep(polling_interval)
                        continue
                
                rr = await self.client.read_holding_registers(address=register_address, count=1, slave=unit_id)

                if rr.isError():
                    logger.error(f"Modbus error reading sensor {sensor.id} (Register: {register_address}): {rr}")
                    value = None
                    status = "Invalid"
                else:
                    value = rr.registers[0]
                    status = "Valid"
                    logger.debug(f"Sensor {sensor.id}: value={value} {sensor.publisher_config.unit}")

                reading = SensorReading(
                    sensor_id=sensor.id,
                    value=value,
                    unit=sensor.publisher_config.unit,
                    status=status,
                    timestamp=datetime.now(timezone.utc),
                    mqtt_topic_suffix=sensor.publisher_config.mqtt_topic_suffix,
                    change_threshold=sensor.publisher_config.change_threshold,
                    min_publish_interval_seconds=sensor.publisher_config.min_publish_interval_seconds
                )
                await data_queue.put(reading)

            except Exception as e:
                logger.error(f"Unexpected error reading Modbus sensor {sensor.id}: {e}", exc_info=True)
                error_reading = SensorReading(
                    sensor_id=sensor.id, value=None, unit=sensor.publisher_config.unit, 
                    status = "Invalid",
                    timestamp=datetime.now(timezone.utc), mqtt_topic_suffix=sensor.publisher_config.mqtt_topic_suffix,
                    change_threshold=sensor.publisher_config.change_threshold,
                    min_publish_interval_seconds=sensor.publisher_config.min_publish_interval_seconds
                )
                await data_queue.put(error_reading)
            
            if not self._running:
                break
            await asyncio.sleep(polling_interval)

    async def start(self, sensors_to_collect: list[SensorConfig], data_queue: asyncio.Queue):
        if not self.config.enabled:
            logger.info("Modbus TCP Collector is disabled by configuration.")
            return

        self._running = True
        await self._connect_client()

        if not self.client.connected and self._running:
             logger.warning(f"Modbus client still not connected to {self.config.host}:{self.config.port}. Sensor loops will attempt reconnections.")

        for sensor_cfg in sensors_to_collect:
            if sensor_cfg.collector_type == "modbus_tcp":
                if sensor_cfg.id in self._sensor_tasks and not self._sensor_tasks[sensor_cfg.id].done():
                    logger.warning(f"Task for Modbus sensor {sensor_cfg.id} already running. Skipping.")
                    continue
                task = asyncio.create_task(self._read_sensor_loop(sensor_cfg, data_queue))
                self._sensor_tasks[sensor_cfg.id] = task
            if not self._running:
                break
        
        if not self._sensor_tasks:
            logger.info("No Modbus TCP sensors configured or enabled for this collector.")

    async def stop(self):
        logger.info("Stopping Modbus TCP Collector...")
        self._running = False
        if self.client.connected:
            await self.client.close()
            logger.info("Modbus client connection closed.")
        
        for sensor_id, task in self._sensor_tasks.items():
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled task for Modbus sensor {sensor_id}")
        
        results = await asyncio.gather(*self._sensor_tasks.values(), return_exceptions=True)
        for sensor_id, result in zip(self._sensor_tasks.keys(), results):
            if isinstance(result, asyncio.CancelledError):
                logger.info(f"Modbus sensor task {sensor_id} was cancelled.")
            elif isinstance(result, Exception):
                logger.error(f"Exception in Modbus sensor task {sensor_id} during shutdown: {result}")
        
        self._sensor_tasks.clear()
        logger.info("Modbus TCP Collector stopped.")

    def is_running(self) -> bool:
        return self._running and any(not task.done() for task in self._sensor_tasks.values())