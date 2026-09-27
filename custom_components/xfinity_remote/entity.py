"""Base entity for Xfinity Remote."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import XfinityRemoteConfigEntry
from .api import XfinityRemoteAuthError, XfinityRemoteError
from .const import DOMAIN, MANUFACTURER, MODEL


class XfinityRemoteEntity(Entity):
    """Common device info and error handling."""

    _attr_has_entity_name = True

    def __init__(self, entry: XfinityRemoteConfigEntry) -> None:
        self._entry = entry
        self._client = entry.runtime_data.client
        device_id = entry.runtime_data.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.runtime_data.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        self._device_id = device_id

    async def _async_call(self, call: Awaitable[None]) -> None:
        """Run an API call, turning failures into Home Assistant errors."""
        try:
            await call
        except XfinityRemoteAuthError as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Xfinity rejected the token; re-pair the remote") from err
        except XfinityRemoteError as err:
            raise HomeAssistantError(f"Xfinity command failed: {err}") from err
