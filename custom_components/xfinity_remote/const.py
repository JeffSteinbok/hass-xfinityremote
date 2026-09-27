"""Constants for the Xfinity Remote integration."""

from datetime import timedelta

DOMAIN = "xfinity_remote"

CONF_TOKEN = "token"
CONF_DEVICE_NAME = "device_name"

MANUFACTURER = "Comcast"
MODEL = "Xfinity X1"

# The web remote refreshes on the interval baked into the token (~50 min today).
DEFAULT_REFRESH_INTERVAL = timedelta(minutes=45)

# EasyPair: how long to wait for the code to be entered on the TV, and how often to poll.
PAIRING_TIMEOUT_SECONDS = 180
PAIRING_POLL_SECONDS = 5

DEFAULT_DELAY_SECS = 0.4

SERVICE_TUNE = "tune"
SERVICE_SEND_TEXT = "send_text"
ATTR_CHANNEL = "channel"
ATTR_TEXT = "text"
