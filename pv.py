import sys
import logging
from pvconf import Conf
from pvinflux import PvInflux
from pvrelay import Relay


# Logger
logger = logging.getLogger("pv")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.info("PyFusionSolarDataRelay started")

# Config
conf = Conf(logger)
if conf.debug:
    logger.debug("Enabled verbose logging")
    logger.setLevel(logging.DEBUG)
    conf.print()
else:
    logger.setLevel(logging.INFO)

# Setup InfluxDB
pvinflux = PvInflux(conf, logger)
pvinflux.initialize()

# Start relay
relay = Relay(conf, pvinflux, logger)
try:
    relay.main()
except KeyboardInterrupt:
    logger.info("Ctrl C - Stopping relay")
    sys.exit(1)
