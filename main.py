import sys
import logging
import time
from threading import Thread
from modules.conf import Conf
from modules.relay_fusionsolar_kiosk import RelayFusionSolarKiosk
from modules.relay_fusionsolar_open_api import RelayFusionSolarOpenApi
from modules.relay_kenter import RelayKenter

# Disable https cert verify disabled warning (Telerik Fiddler)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logger
logger: logging.Logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.info("PyFusionSolarDataRelay 2.0.1 started")

# Config
conf = Conf(logger).read_and_validate_config()
if conf.debug_mode:
    logger.debug("Enabled verbose logging")
    logger.setLevel(logging.DEBUG)
    logger.debug(conf.model_dump_json(indent=2, exclude_defaults=False))
else:
    logger.setLevel(logging.INFO)
    # logger.info(conf.model_dump_json(indent=2, exclude_defaults=False))

# Start RelayFusionSolar and KenterRelay
try:
    if __name__ == "__main__":
        if conf.fusionsolar_kiosk_module_enabled:
            fs_thread = Thread(target=RelayFusionSolarKiosk, args=[conf, logger])
            fs_thread.daemon = True
            fs_thread.start()
        if conf.fusionsolar_open_api_module_enabled:
            fs_thread = Thread(target=RelayFusionSolarOpenApi, args=[conf, logger])
            fs_thread.daemon = True
            fs_thread.start()
        if conf.kenter_module_enabled:
            gr_thread = Thread(target=RelayKenter, args=[conf, logger])
            gr_thread.daemon = True
            gr_thread.start()
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Ctrl C - Stopping relay")
    sys.exit(0)
