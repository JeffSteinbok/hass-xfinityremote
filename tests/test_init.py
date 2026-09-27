"""Setup and token refresh tests."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.xfinity_remote.api import XfinityRemoteAuthError, XfinityRemoteError
from custom_components.xfinity_remote.const import CONF_DEVICE_NAME, CONF_TOKEN, DOMAIN

from .conftest import DEVICE_ID, make_token


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=DEVICE_ID, data={CONF_TOKEN: make_token(), CONF_DEVICE_NAME: "Family Room"}
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_refreshes_and_saves_token(hass: HomeAssistant, mock_client) -> None:
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data[CONF_TOKEN] == mock_client.refreshed
    assert hass.states.get("remote.family_room") is not None
    assert hass.states.get("button.family_room_guide") is not None
    # Digits are created but disabled by default.
    assert hass.states.get("button.family_room_7") is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_periodic_refresh(hass: HomeAssistant, mock_client) -> None:
    entry = _entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    calls = mock_client.refresh_token.call_count

    # The refreshed token advertises a ~50 minute interval.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=51))
    await hass.async_block_till_done()
    assert mock_client.refresh_token.call_count == calls + 1


async def test_refresh_rejected_starts_reauth(hass: HomeAssistant, mock_client) -> None:
    entry = _entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mock_client.refresh_token.side_effect = XfinityRemoteAuthError("expired")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=51))
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_setup_auth_failure(hass: HomeAssistant, mock_client) -> None:
    mock_client.refresh_token.side_effect = XfinityRemoteAuthError("expired")
    entry = _entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress())


async def test_setup_network_failure_retries(hass: HomeAssistant, mock_client) -> None:
    mock_client.refresh_token.side_effect = XfinityRemoteError("down")
    entry = _entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
