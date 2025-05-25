import yaml
from pathlib import Path
import logging
from .models.config_models import AppConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "gateway_config.default.yml"
USER_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "gateway_config.yml"

def load_config() -> AppConfig:
    config_path_to_load = None
    config_data = {}

    if USER_CONFIG_PATH.exists():
        config_path_to_load = USER_CONFIG_PATH
        logger.info(f"Loading user configuration from: {USER_CONFIG_PATH}")
    elif DEFAULT_CONFIG_PATH.exists():
        config_path_to_load = DEFAULT_CONFIG_PATH
        logger.info(f"User configuration not found. Loading default: {DEFAULT_CONFIG_PATH}")
        logger.warning(f"Tip: Copy '{DEFAULT_CONFIG_PATH.name}' to '{USER_CONFIG_PATH.name}' to customize.")
    else:
        logger.error("CRITICAL: No configuration file found (default or user). Cannot start.")
        raise FileNotFoundError("Configuration file (gateway_config.default.yml or gateway_config.yml) not found.")

    with open(config_path_to_load, 'r') as f:
        config_data = yaml.safe_load(f)

    try:
        app_config = AppConfig(**config_data)
        logger.info("Configuration loaded and validated.")
        return app_config
    except Exception as e:
        logger.error(f"Error validating configuration from {config_path_to_load}: {e}")
        raise