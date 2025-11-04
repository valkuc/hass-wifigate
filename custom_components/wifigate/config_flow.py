"""WifiGate config flow."""

import logging
from typing import Any

import aiohttp
from homeassistant import config_entries
from homeassistant.config_entries import ConfigError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
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
    MINOR_VERSION = 0

    async def async_step_user(self, user_input=None):
        """Handle configuration flow initiated by the user."""
        errors: dict[str, str] = {}
        if user_input:
            host = user_input.get(CONF_HOST)
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            try:
                await self._test_connection(host, username, password)
            except Exception as exc:
                _LOGGER.error("Connection test failed: %s", exc)
                errors["base"] = str(exc)
            else:
                return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self._create_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle reconfiguration flow initiated by the user."""
        entry = self.hass.config_entries.async_get_known_entry(self.context["entry_id"])
        errors: dict[str, str] = {}
        if user_input:
            host = user_input.get(CONF_HOST)
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            try:
                await self._test_connection(host, username, password)
            except Exception as exc:
                _LOGGER.error("Connection test failed: %s", exc)
                errors["base"] = str(exc)
            else:
                return self.async_update_reload_and_abort(entry, data=user_input)

        if entry and not user_input:
            user_input = entry.data

        return self.async_show_form(
            step_id="reconfigure", data_schema=self._create_schema(user_input)
        )

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
    def _create_schema(user_input: dict[str, Any] | None = None):
        controls_selector = SelectSelector(
            SelectSelectorConfig(
                options=DEFAULT_CONTROLS,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_CONTROLS,
            )
        )

        if user_input:
            base_schema = {
                vol.Required(CONF_NAME, default=user_input.get(CONF_NAME)): str,
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): str,
                vol.Optional(
                    CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")
                ): str,
                vol.Optional(
                    CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                ): str,
                vol.Required(
                    CONF_CONTROLS,
                    default=user_input.get(CONF_CONTROLS, DEFAULT_CONTROLS),
                ): controls_selector,
            }
        else:
            base_schema = {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Required(
                    CONF_CONTROLS, default=DEFAULT_CONTROLS
                ): controls_selector,
            }

        return vol.Schema(base_schema)
