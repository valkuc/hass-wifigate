"""Support for WifiGate button entities."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMMAND_MAP, CONF_CONTROLS, DOMAIN
from .coordinator import WifigateDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up buttons from a config entry."""

    coordinator: WifigateDataUpdateCoordinator = config_entry.runtime_data
    controls = config_entry.data.get(CONF_CONTROLS)
    entity_registry = async_get(hass)

    for ctrl in COMMAND_MAP:
        if ctrl not in controls:
            entity_id = entity_registry.async_get_entity_id(
                Platform.BUTTON,
                DOMAIN,
                WifigateControlButton.get_entity_unique_id(config_entry, ctrl),
            )
            if entity_id:
                entity_registry.async_remove(entity_id)

    buttons = [
        WifigateControlButton(coordinator, config_entry, ctrl)
        for ctrl in controls
        if ctrl in COMMAND_MAP
    ]
    async_add_entities(buttons)


class WifigateControlButton(
    CoordinatorEntity[WifigateDataUpdateCoordinator], ButtonEntity
):
    """Button entity for controlling the gate with one-shot commands."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WifigateDataUpdateCoordinator,
        config_entry: ConfigEntry,
        control: str,
    ):
        """Initialize control button."""
        super().__init__(coordinator)
        self.control = control
        self._attr_translation_key = f"control_{control}"
        self._attr_unique_id = self.get_entity_unique_id(config_entry, control)
        self._attr_device_info = self.coordinator.get_device_info()

    async def async_press(self):
        """Send command when button is pressed."""
        try:
            await self.coordinator.send_command(COMMAND_MAP[self.control])
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to send command '%s': %s", self.control, e)
            raise

    @property
    def icon(self):
        """Return icon."""
        return {
            "open": "mdi:door-sliding-open",
            "close": "mdi:door-sliding",
            "stop": "mdi:stop-circle-outline",
            "step": "mdi:step-forward-2",
            "wicket": "mdi:human-male",
        }.get(self.control)

    @staticmethod
    def get_entity_unique_id(config_entry: ConfigEntry, control: str):
        """Build unique ID."""
        return f"{config_entry.entry_id}_ctl_{control}"
