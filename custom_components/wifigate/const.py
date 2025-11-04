"""Constants for the WifiGate integration."""

DOMAIN = "wifigate"
NAME = "WifiGate"

# Configuration keys
CONF_NAME = "name"
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CONTROLS = "controls"

# Default values
DEFAULT_CONTROLS = ["open", "close", "stop", "step", "wicket"]
DEFAULT_NAME = "Ворота"

# Request timeout in seconds
REQUEST_TIMEOUT = 5.0

# State polling interval in seconds
POLL_INTERVAL = 2.0

COMMAND_MAP = {
    "open": 0,
    "close": 1,
    "stop": 2,
    "step": 3,
    "wicket": 4,
}

STATE_MAP = {
    0: "unknown",
    1: "opening",
    2: "open",
    3: "closing",
    4: "closed",
    5: "wicket",
    6: "stopped",
}
