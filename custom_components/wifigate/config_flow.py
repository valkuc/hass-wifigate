"""WifiGate config flow."""

import logging
import re
from typing import Any, Mapping
from urllib.parse import urlparse

import aiohttp
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigEntry, ConfigError
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    SsdpServiceInfo,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
import voluptuous as vol

from .const import (
    CONF_CONTROLS,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_CONTROLS,
    DEFAULT_NAME,
    DOMAIN,
    NAME,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class WifigateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """WifiGate config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.wg_config: dict[str, Any] = {}

    async def async_step_user(self, user_input=None):
        """Handle configuration flow initiated by the user."""
        errors: dict[str, str] = {}
        wg_config = self.wg_config
        if user_input:
            wg_config.update(user_input)

            host = user_input.get(CONF_HOST)
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            try:
                await self._test_connection(host, username, password)
            except Exception as exc:
                _LOGGER.error("Connection test failed: %s", exc)
                errors["base"] = str(exc) or "Unable to connect"
            else:
                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data=wg_config
                    )
                return self.async_create_entry(title=NAME, data=wg_config)

        return self.async_show_form(
            step_id="user",
            data_schema=self._create_schema(wg_config),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle reconfiguration flow initiated by the user."""
        entry = self._get_reconfigure_entry()
        self.wg_config.update(entry.data)
        return await self.async_step_user()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo):
        """Prepare configuration for a discovered mDNS device."""
        _LOGGER.debug("mDNS discovery_info: %s", discovery_info)
        _LOGGER.debug("mDNS discovery_info: %s", repr(discovery_info))

        self._async_abort_entries_match({CONF_HOST: discovery_info.host})
        await self._async_handle_discovery_without_unique_id()

        self.wg_config = {
            CONF_HOST: discovery_info.host,
            CONF_NAME: self._extract_name_mdns(discovery_info.name),
        }
        return await self.async_step_user()

    async def async_step_ssdp(self, discovery_info: SsdpServiceInfo):
        """Prepare configuration for a discovered SSDP device."""
        _LOGGER.debug("SSDP discovery_info: %s", discovery_info)

        parsed_url = urlparse(discovery_info.ssdp_location)
        friendly_name = self._extract_name_ssdp(
            discovery_info.upnp[ATTR_UPNP_FRIENDLY_NAME]
        )

        self._async_abort_entries_match({CONF_HOST: parsed_url.hostname})
        await self._async_handle_discovery_without_unique_id()

        self.wg_config = {
            CONF_HOST: parsed_url.hostname,
            CONF_NAME: friendly_name,
        }
        return await self.async_step_user()

    @property
    def _reconfigure_entry_id(self) -> str:
        """Return reconfigure entry id."""
        if self.source != SOURCE_RECONFIGURE:
            raise ValueError(f"Source is {self.source}, expected {SOURCE_RECONFIGURE}")
        return self.context["entry_id"]

    @callback
    def _get_reconfigure_entry(self) -> ConfigEntry:
        """Return the reconfigure config entry linked to the current context."""
        return self.hass.config_entries.async_get_known_entry(
            self._reconfigure_entry_id
        )

    @staticmethod
    def _extract_name_ssdp(name: str):
        match = re.search(r" \((.+)\)", name)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_name_mdns(name: str):
        match = re.search(r"(.+)._wifigate._tcp.local.", name)
        if match:
            return match.group(1)
        return None

    @staticmethod
    async def _test_connection(host: str, username, password):
        url = f"http://{host}/robots.txt"
        auth = aiohttp.BasicAuth(username, password) if username else None
        async with aiohttp.ClientSession(auth=auth) as session, session.get(
            url, timeout=REQUEST_TIMEOUT
        ) as resp:
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN, translation_key="auth_fail"
                )
            if resp.status != 200:
                raise ConfigError(f"HTTP {resp.status}")

    @staticmethod
    def _create_schema(user_input: Mapping[str, Any]) -> vol.Schema:
        """Generate base schema."""
        base_schema = {
            vol.Required(
                CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)
            ): str,
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): str,
            vol.Optional(CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")): str,
            vol.Optional(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")): str,
            vol.Required(
                CONF_CONTROLS,
                default=user_input.get(CONF_CONTROLS, DEFAULT_CONTROLS),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=DEFAULT_CONTROLS,
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_CONTROLS,
                )
            ),
        }

        return vol.Schema(base_schema)
