"""Remote and button entity tests."""

from unittest.mock import call, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xfinity_remote.api import XfinityRemoteAuthError
from custom_components.xfinity_remote.const import CONF_DEVICE_NAME, CONF_TOKEN, DOMAIN

from .conftest import DEVICE_ID, make_token

REMOTE = "remote.family_room"


@pytest.fixture
async def setup(hass: HomeAssistant, mock_client):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=DEVICE_ID, data={CONF_TOKEN: make_token(), CONF_DEVICE_NAME: "Family Room"}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    with patch("custom_components.xfinity_remote.remote.asyncio.sleep"):
        yield mock_client


async def test_send_command_variants(hass: HomeAssistant, setup) -> None:
    await hass.services.async_call(
        "remote", "send_command",
        {"entity_id": REMOTE, "command": ["guide", "PAGE_DOWN", "42", "volume_up"]},
        blocking=True,
    )
    assert setup.send_key.call_args_list == [
        call("GUIDE"), call("PAGE_DOWN"), call("NUMBER_4"), call("NUMBER_2"),
    ]
    setup.send_cec_key.assert_called_once_with("VOLUME", "UP")


async def test_send_command_repeats(hass: HomeAssistant, setup) -> None:
    await hass.services.async_call(
        "remote", "send_command",
        {"entity_id": REMOTE, "command": "right", "num_repeats": 3},
        blocking=True,
    )
    assert setup.send_key.call_args_list == [call("RIGHT")] * 3


async def test_unknown_command(hass: HomeAssistant, setup) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "remote", "send_command", {"entity_id": REMOTE, "command": "self_destruct"}, blocking=True
        )
    setup.send_key.assert_not_called()


async def test_tune_and_text(hass: HomeAssistant, setup) -> None:
    await hass.services.async_call(DOMAIN, "tune", {"entity_id": REMOTE, "channel": "702"}, blocking=True)
    assert setup.send_key.call_args_list == [call("NUMBER_7"), call("NUMBER_0"), call("NUMBER_2")]

    await hass.services.async_call(DOMAIN, "send_text", {"entity_id": REMOTE, "text": "watch ESPN"}, blocking=True)
    setup.send_text.assert_called_once_with("watch ESPN")


async def test_button_press(hass: HomeAssistant, setup) -> None:
    await hass.services.async_call("button", "press", {"entity_id": "button.family_room_guide"}, blocking=True)
    setup.send_key.assert_called_once_with("GUIDE")
    await hass.services.async_call("button", "press", {"entity_id": "button.family_room_mute"}, blocking=True)
    setup.send_cec_key.assert_called_once_with("MUTE", "ON")


async def test_auth_error_on_command_starts_reauth(hass: HomeAssistant, setup) -> None:
    setup.send_key.side_effect = XfinityRemoteAuthError("expired")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("button", "press", {"entity_id": "button.family_room_ok"}, blocking=True)
    await hass.async_block_till_done()
    assert any(f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress())
