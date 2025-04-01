import sys
import logging
import time
from threading import Thread
from modules.conf import Conf
from modules.relay_fusionsolar import RelayFusionSolar
from modules.relay_meetdata import RelayMeetdata

# Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.info("PyFusionSolarDataRelay 1.1.0 started")

# Config
conf = Conf(logger).read_and_validate_config()
if conf.debug_mode:
    logger.debug("Enabled verbose logging")
    logger.setLevel(logging.DEBUG)
    print(conf.model_dump_json())
else:
    logger.setLevel(logging.INFO)

# Start RelayFusionSolar and KenterRelay
try:
    if __name__ == '__main__':
        if conf.fusionsolar_kiosk_enabled:
            fs_thread = Thread(target = RelayFusionSolar, args=[conf, logger])
            fs_thread.daemon = True
            fs_thread.start()
        if conf.meetdata_nl_enabled:
            gr_thread = Thread(target = RelayMeetdata, args=[conf, logger])
            gr_thread.daemon = True
            gr_thread.start()
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Ctrl C - Stopping relay")
    sys.exit(0)

