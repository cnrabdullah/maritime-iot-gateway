import logging
import sys
from ..models.config_models import LoggingConfig

def setup_logging(config: LoggingConfig):
    logging.basicConfig(
        level=config.level,
        format=config.format,
        datefmt=config.date_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Level: {config.level}")