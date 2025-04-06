import os
import pathlib
from modules.conf_models import *
from dotenv import load_dotenv

DOTENV = f"{pathlib.Path(__file__).resolve().parent.parent}/.env"

class Conf:
    def __init__(self, logger):
        self.logger = logger
        self.logger.debug("Config class instantiated")

    def read_and_validate_config(self) -> PyFusionSolarSettings:
        
        # DOTENV processing
        self.logger.debug(f"DOTENV config file path: {DOTENV}")
        if os.path.exists(DOTENV):
            self.logger.info(f"DOTENV config file exists, loading settings from .env file...")
            try:
                load_dotenv(dotenv_path=DOTENV, encoding='utf-8')
                self.logger.debug("Loaded environment variables from file.")
            except (Exception) as e:
                self.logger.exception(f"Error while loading DOTENV file from {DOTENV}: {e}")
                raise
        else:
            self.logger.info(f"No DOTENV config file found in pyfusionsolar working dir. Using environment variables from environment or default settings.")

        # Class instantiating
        config = PyFusionSolarSettings()
        return config