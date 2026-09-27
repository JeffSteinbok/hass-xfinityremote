# Xfinity Remote for Home Assistant

Control an Xfinity X1 cable box from Home Assistant, using the same cloud API as
[Xfinity's web remote](https://remote.xfinity.com). No hub, IR blaster, or local network
access to the box is needed. Button presses go through Xfinity's servers, just like
they do from the web remote.

> This is an unofficial integration. It isn't affiliated with or endorsed by Comcast.
> Xfinity and the Xfinity logo are trademarks of Comcast.

## Installation (HACS)

1. In HACS, open the ⋮ menu → **Custom repositories**.
2. Add `https://github.com/jeffsteinbok/hass-xfinityremote` with the **Integration** category.
3. Install **Xfinity Remote** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → Xfinity Remote**.

## Pairing

Choose **Pair with EasyPair**. Home Assistant shows a 7-digit code:

1. Pick up your Xfinity voice remote and say **"Easy Pair"**.
2. Enter the code on the TV and select **Pair Now**.
3. Home Assistant finishes setup automatically as soon as the TV confirms.

Pairing gives Home Assistant its own long-lived token for that box. The web remote's
tokens last about six months, and the integration renews its token on the server's
schedule (about every 50 minutes), so it shouldn't expire while Home Assistant is running. If Xfinity ever rejects it, Home Assistant
asks you to pair again.

**Alternative:** choose **Paste a token**, sign in at remote.xfinity.com, run
`localStorage.arToken` in the browser console, and paste the result.

## What you get

- **`remote.<box name>`**: a remote entity for `remote.send_command`.
- **Button entities** for the common keys (arrows, OK, Guide, Menu, playback, channel, and
  volume). Number keys, color keys, and TV power/input are created disabled; turn them on
  from the entity list if you want them.
- **Services**: `xfinity_remote.tune` and `xfinity_remote.send_text`.

### Commands

`remote.send_command` accepts any of these:

| Kind | Examples |
|---|---|
| Key name | `guide`, `menu`, `ok`, `up`, `exit`, `last`, `info`, `play_pause`, `rewind`, `fast_forward`, `record`, `replay`, `channel_up`, `page_down`, `key_a`…`key_d`, `number_0`…`number_9` |
| Raw vcode | `GUIDE`, `ENTER`, `PREV`, `COLOR_KEY_0`, `NUMBER_7`, … |
| Digits | `"702"` types 7, 0, 2 |
| TV (HDMI-CEC) | `volume_up`, `volume_down`, `tv_mute`, `tv_input`, `tv_power_off` |

TV keys use HDMI-CEC and only work if your TV supports CEC control from the box.

### Examples

```yaml
# Tune to a channel
action: xfinity_remote.tune
target:
  entity_id: remote.family_room
data:
  channel: "702"
```

```yaml
# Anything you could say into the voice remote
action: xfinity_remote.send_text
target:
  entity_id: remote.family_room
data:
  text: "watch ESPN"
```

```yaml
# Open the guide and page down twice
action: remote.send_command
target:
  entity_id: remote.family_room
data:
  command: [guide, page_down, page_down]
  delay_secs: 0.5
```

## Logo

The Xfinity logo appears on the integration card on Home Assistant 2026.3 and later, which
added support for custom integrations shipping their own brand images. The integration
works on 2025.2 and later; older versions just show a placeholder logo.

## How it works

This integration was built by reverse-engineering remote.xfinity.com. The API is
unofficial and Comcast could change it at any time. Endpoints used:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/pairing/start`, `/pairing/confirm` | EasyPair code and polling |
| `POST /api/v1/auth/token/refresh` | Token renewal |
| `POST /api/v1/devices` | Box name lookup |
| `POST /api/v1/processKey` `{vcode}` | Box key presses |
| `POST /api/v1/processCecKey` `{key, value}` | TV keys over HDMI-CEC |
| `POST /api/v1/text` `{cmd, arToken}` | Voice-style text commands |

## Development

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.test.txt pylint
.venv/bin/pytest
```
