import asyncio
import logging
import signal
from typing import Optional

from .config_loader import load_config
from .utils.logging_setup import setup_logging
from .models.config_models import AppConfig
from .gateway_manager import GatewayManager

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [Pre-Config] %(message)s")
logger = logging.getLogger(__name__) 

async def _main_async():
    gateway_manager: Optional[GatewayManager] = None
    shutdown_event = asyncio.Event()

    def signal_handler(*args):
        logger.info("Shutdown signal received...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        config: AppConfig = load_config()
        setup_logging(config.logging)
        logger.info(f"Starting {config.application_name}...")
        gateway_manager = GatewayManager(config)
        manager_task = asyncio.create_task(gateway_manager.start())
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        done, pending = await asyncio.wait(
            [manager_task, shutdown_task], 
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if manager_task in done and manager_task.exception():
            logger.error(f"GatewayManager exited with error: {manager_task.exception()}", exc_info=manager_task.exception())
        
    except Exception as e:
        logging.getLogger("Bootstrap").error(f"CRITICAL: Unexpected startup error: {e}", exc_info=True)
    finally:
        if gateway_manager:
            logger.info("Initiating final shutdown of GatewayManager...")
            await gateway_manager.stop()
        logger.info(f"Application shutdown complete.")

def run_gateway():
    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        logger.info("Exiting via KeyboardInterrupt (fallback).")
    except Exception as e:
        logger.critical(f"Unhandled exception in run_gateway: {e}", exc_info=True)


if __name__ == "__main__":
    run_gateway()