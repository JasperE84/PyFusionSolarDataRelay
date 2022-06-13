import sys
import logging
from pvconf import PvConf
from pvrelay import PvRelay

# Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.info("PyFusionSolarDataRelay 1.0.2 started")

# Config
conf = PvConf(logger)
if conf.debug:
    logger.debug("Enabled verbose logging")
    logger.setLevel(logging.DEBUG)
    conf.print()
else:
    logger.setLevel(logging.INFO)

# Start relay
relay = PvRelay(conf, logger)
try:
    relay.main()
except KeyboardInterrupt:
    logger.info("Ctrl C - Stopping relay")
    sys.exit(0)
