from abc import ABC, abstractmethod
import asyncio
import logging
from ..models.config_models import SensorConfig
from ..models.sensor_reading import SensorReading
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

DataCallback = Callable[[SensorReading], Awaitable[None]]

class BaseCollector(ABC):
    def __init__(self, general_config: ...) -> None:
        self.general_config = general_config
        self._tasks: list[asyncio.Task] = []

    @abstractmethod
    async def start(self, sensors: list[SensorConfig], data_queue: asyncio.Queue):
        """
        Starts the collector and its data collection tasks for the given sensors.
        Collected data (SensorReading objects) should be put into data_queue.
        """
        pass

    async def stop(self):
        """
        Stops all running tasks for the collector.
        """
        logger.info(f"Stopping collector: {self.__class__.__name__}")
        for task in self._tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info(f"Collector {self.__class__.__name__} stopped.")

    def is_running(self) -> bool:
        return any(not task.done() for task in self._tasks)
