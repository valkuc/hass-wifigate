import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import WifigateDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up sensor from a config entry."""

    coordinator: WifigateDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities([WifigateStateSensor(coordinator, config_entry)])


class WifigateStateSensor(CoordinatorEntity[WifigateDataUpdateCoordinator], SensorEntity):
    """Sensor to display the current state of the gate."""

    _attr_has_entity_name = True
    _attr_translation_key = "state_sensor"
    _attr_state_class = None
    _attr_device_class = "door"
    _attr_icon = "mdi:gate"

    def __init__(self, coordinator: WifigateDataUpdateCoordinator, config_entry: ConfigEntry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_state"
        self._attr_device_info = self.coordinator.get_device_info()

    @property
    def native_value(self):
        return self.coordinator.data["state"]

    @property
    def extra_state_attributes(self):
        return {
            "raw_state": self.coordinator.data["state_value"],
            "last_updated": self.coordinator.data["last_updated"].isoformat(),
        }
