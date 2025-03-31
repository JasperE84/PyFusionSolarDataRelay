import os
import yaml
from modules.conf_models import *
from pydantic import ValidationError

class Conf:
    def __init__(self, logger):
        self.logger = logger
        self.logger.debug("Config class instantiated")

    def read_and_validate_config(self) -> BaseConf:
        config_file = os.path.join(os.path.dirname(__file__), os.path.pardir, "config.yaml")
        self.logger.info(f"Config file path: {config_file}")

        if os.path.exists(config_file):
            self.logger.info(f"File exists, safe_loading yaml...")
            with open(config_file, "r") as file:
                try:
                    user_config = yaml.safe_load(file) or {}
                    BaseConf.validate(user_config)
                    self.logger.debug("Validated user config")
                    config = BaseConf(**user_config)
                    self.logger.info("Parsed configuration file.")
                except (ValidationError, Exception) as e:
                    self.logger.exception(f"Error while parsing yaml file: {e}")
                    raise
        else:
            self.logger.info(f"No config file found, using default values.")
            config = BaseConf()

        return config
    
    def dump_config_as_yaml(self, conf: BaseConf, skip_defaults: bool, output_file: str = "config.yaml.dump"):
        settings_dict = conf.dict(skip_defaults=skip_defaults)
        yaml_str = yaml.dump(settings_dict, indent=4)
    
        with open(output_file, 'w') as file:
            file.write(yaml_str)

