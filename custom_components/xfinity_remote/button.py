"""Button entities, one per key on the Xfinity web remote."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import XfinityRemoteConfigEntry
from .api import CEC_KEYS, KEYS
from .entity import XfinityRemoteEntity

# Everything else (digits, color keys, TV power/input) is created disabled to keep the
# device page tidy; enable them from the entity list if you want them.
ENABLED_BY_DEFAULT = {
    "up",
    "down",
    "left",
    "right",
    "ok",
    "exit",
    "last",
    "menu",
    "guide",
    "info",
    "channel_up",
    "channel_down",
    "play_pause",
    "rewind",
    "fast_forward",
    "replay",
    "record",
    "volume_up",
    "volume_down",
    "tv_mute",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XfinityRemoteConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the key buttons."""
    async_add_entities(XfinityKeyButton(entry, key) for key in (*KEYS, *CEC_KEYS))


class XfinityKeyButton(XfinityRemoteEntity, ButtonEntity):
    """Presses a single remote key."""

    def __init__(self, entry: XfinityRemoteConfigEntry, key: str) -> None:
        super().__init__(entry)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{self._device_id}_{key}"
        self._attr_entity_registry_enabled_default = key in ENABLED_BY_DEFAULT

    async def async_press(self) -> None:
        """Send the key."""
        if self._key in CEC_KEYS:
            await self._async_call(lambda: self._client.send_cec_key(*CEC_KEYS[self._key]))
        else:
            await self._async_call(lambda: self._client.send_key(KEYS[self._key]))
