import asyncio
import logging
import signal
from typing import Optional

from .config_loader import load_config
from .utils.logging_setup import setup_logging
from .models.config_models import AppConfig
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [Pre-Config] %(message)s")
logger = logging.getLogger(__name__) 

async def _main_async():
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
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        done, pending = await asyncio.wait(
            [shutdown_task], 
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

    except Exception as e:
        logging.getLogger("Bootstrap").error(f"CRITICAL: Unexpected startup error: {e}", exc_info=True)
    finally:
        logger.info(f"Application shutdown complete.")


if __name__ == "__main__":
    run_gateway()