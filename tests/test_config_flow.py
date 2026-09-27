"""Config flow tests."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xfinity_remote.api import XfinityRemoteAuthError
from custom_components.xfinity_remote.const import CONF_DEVICE_NAME, CONF_TOKEN, DOMAIN

from .conftest import DEVICE_ID, make_token


async def _start_pairing(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "pair"})
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["description_placeholders"] == {"code": "1234567"}
    return result


async def test_easypair_creates_entry(hass: HomeAssistant, mock_client) -> None:
    result = await _start_pairing(hass)
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Family Room"
    assert result["data"] == {CONF_TOKEN: make_token(), CONF_DEVICE_NAME: "Family Room"}
    assert result["result"].unique_id == DEVICE_ID


async def test_easypair_timeout_then_retry(hass: HomeAssistant, mock_client) -> None:
    mock_client.confirm_pairing.return_value = None
    with patch("custom_components.xfinity_remote.config_flow.PAIRING_TIMEOUT_SECONDS", 0.05):
        result = await _start_pairing(hass)
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pair_failed"
    assert result["errors"] == {"base": "pair_timeout"}

    mock_client.confirm_pairing.return_value = make_token()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_client.start_pairing.call_count == 2


async def test_easypair_already_configured(hass: HomeAssistant, mock_client) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=DEVICE_ID, data={CONF_TOKEN: "old"}).add_to_hass(hass)
    result = await _start_pairing(hass)
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_token(hass: HomeAssistant, mock_client) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    assert result["step_id"] == "token"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: f" {make_token()} "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # The pasted token is exchanged for a fresh one before saving.
    assert result["data"][CONF_TOKEN] == mock_client.refreshed


async def test_manual_token_rejected(hass: HomeAssistant, mock_client) -> None:
    mock_client.refresh_token.side_effect = XfinityRemoteAuthError("nope")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: make_token()})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: "garbage"})
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth(hass: HomeAssistant, mock_client) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DEVICE_ID, data={CONF_TOKEN: "old", CONF_DEVICE_NAME: "Family Room"})
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "pair"})
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] != "old"


async def test_reauth_wrong_device(hass: HomeAssistant, mock_client) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="some-other-box", data={CONF_TOKEN: "old"})
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "pair"})
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["reason"] == "wrong_device"
