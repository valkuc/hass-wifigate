import logging
from datetime import timedelta
from typing import Any, Dict

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import InvalidStateError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)
from homeassistant.util.dt import utcnow

from .const import (CONF_CONTROLS, CONF_HOST, CONF_NAME, CONF_PASSWORD,
                    CONF_USERNAME, DOMAIN, NAME, POLL_INTERVAL,
                    REQUEST_TIMEOUT, STATE_MAP)


class WifigateDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the WifiGate API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(
            hass=hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}_{entry.data.get(CONF_HOST)}",
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )
        self.entry = entry
        self.host = entry.data.get(CONF_HOST)
        self.username = entry.data.get(CONF_USERNAME)
        self.password = entry.data.get(CONF_PASSWORD)
        self.controls = entry.data.get(CONF_CONTROLS)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch current state from the device."""

        url = f"http://{self.host}/state.cgi"
        auth = aiohttp.BasicAuth(self.username, self.password) if self.username or self.password else None

        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP {resp.status}: {await resp.text()}")
                    data = await resp.json()

                    state_value = data.get("state")
                    state_str = STATE_MAP.get(state_value, STATE_MAP.get(0))

                    return {
                        "state": state_str,
                        "state_value": state_value,
                        "last_updated": utcnow(),
                    }
        except Exception as e:
            self.logger.warning("Unable to fetch state - %s", repr(e))
            if isinstance(e, TimeoutError):
                raise UpdateFailed(translation_domain=DOMAIN, translation_key="timeout")
            raise UpdateFailed(f"Unable to fetch state: {e}")

    async def send_command(self, cmd: int) -> bool:
        """Send a command to the controller."""

        url = f"http://{self.host}/control.cgi?cmd={cmd}"
        auth = aiohttp.BasicAuth(self.username, self.password) if self.username or self.password else None

        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.post(url, timeout=REQUEST_TIMEOUT) as resp:
                    if resp.status == 200 or resp.status == 202:
                        return True
                    elif resp.status == 400:
                        raise InvalidStateError(translation_domain=DOMAIN, translation_key="invalid_param")
                    elif resp.status == 409:
                        raise InvalidStateError(translation_domain=DOMAIN, translation_key="wrong_state")
                    elif resp.status == 423:
                        raise InvalidStateError(translation_domain=DOMAIN, translation_key="busy")
                    else:
                        raise UpdateFailed(f"HTTP {resp.status}")
        except Exception as e:
            self.logger.error("Command failed: %s", repr(e))
            if isinstance(e, TimeoutError):
                raise UpdateFailed(translation_domain=DOMAIN, translation_key="timeout")
            raise

    def get_device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.data.get(CONF_NAME),
            manufacturer=NAME,
            model="WG-11"
        )
