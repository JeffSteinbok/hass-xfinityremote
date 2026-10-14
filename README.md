# Xfinity Remote for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

[![CI Validation](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/ci.yaml/badge.svg)](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/ci.yaml)
[![HACS Validation](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/hacs_validate.yaml/badge.svg)](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/hacs_validate.yaml)
[![hassfest Validation](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/hassfest.yaml)
[![Release Automation](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/release.yaml/badge.svg)](https://github.com/JeffSteinbok/hass-xfinityremote/actions/workflows/release.yaml)

<p align="center">
  <img src="custom_components/xfinity_remote/brand/logo@2x.png" alt="Xfinity" width="300">
</p>

Community Home Assistant integration for controlling an Xfinity X1 cable box. It uses the
same cloud API as [Xfinity's web remote](https://remote.xfinity.com), so there's no hub, IR
blaster, or local network access to the box needed. Button presses go through Xfinity's
servers, just like they do from the web remote. I do not work for Comcast; this is just
something I'm doing for fun.

> [!NOTE]
> This is an unofficial integration. It isn't affiliated with or endorsed by Comcast.
> Xfinity and the Xfinity logo are trademarks of Comcast.

> [!IMPORTANT]
> The API this integration uses was reverse-engineered from remote.xfinity.com. It is not
> published by Comcast and could change at any time. If something suddenly stops working,
> please open an [issue](https://github.com/JeffSteinbok/hass-xfinityremote/issues) with
> debug logs.

> This documentation is intended to be accurate for the branch/tag it's in. If you are
> installing a specific version (including latest) of the integration, please change the
> current viewing tag in GitHub to see the matching documentation.

## Table of Contents

- [Compatibility](#compatibility)
- [Installation](#installation)
- [Initial Configuration](#initial-configuration)
- [Entities and Services](#entities-and-services)
- [Examples](#examples)
- [Debugging](#debugging)
- [How It Works](#how-it-works)
- [Contributing](#contributing)

## Compatibility

- **Boxes:** Xfinity X1 set-top boxes that work with the [Xfinity web remote](https://remote.xfinity.com).
- **Home Assistant:** 2025.2 or later. The Xfinity logo appears on the integration card on
  2026.3 and later, which added support for custom integrations shipping their own brand
  images; older versions show a placeholder logo.
- **TV keys** (volume, mute, input, power off) are sent over HDMI-CEC from the box and only
  work if your TV supports CEC control.

## Installation

### HACS (Recommended)

1. Open `HACS`.
2. Open the ⋮ menu (top right) and choose `Custom repositories`.
3. Add `https://github.com/JeffSteinbok/hass-xfinityremote` with the type `Integration`.
4. Search `Xfinity Remote`, open it, and click `Download`.
5. Restart Home Assistant.

### Manually

Copy the `custom_components/xfinity_remote` directory into your `/config/custom_components`
directory, then restart Home Assistant.

## Initial Configuration

1. In HA, open `Settings`
2. Click `Devices & services`
3. Click `Add integration` (blue button at the bottom right of the screen)
4. Search `Xfinity Remote` and select it
5. Choose how to connect:

### Pair with EasyPair (Recommended)

Home Assistant shows a 7-digit code:

1. Pick up your Xfinity voice remote and say **"Easy Pair"**.
2. Enter the code on the TV and select **Pair Now**.
3. Home Assistant finishes setup automatically as soon as the TV confirms (you have 3 minutes).

### Paste a token

1. Sign in at [remote.xfinity.com](https://remote.xfinity.com) and pair it with your box.
2. Open the browser's developer console and run `localStorage.arToken`.
3. Paste the result (without the quotes) into Home Assistant.

### About the token

You never give Home Assistant your Xfinity username or password. Pairing gives Home
Assistant its own long-lived token bound to **that one box**; it can press buttons on the
box but can't see or change anything on your Xfinity account.

The token lasts about six months, and the integration renews it on the server's schedule
(about every 50 minutes), so it shouldn't expire while Home Assistant is running. If Xfinity
ever rejects it, Home Assistant flags the integration in **Devices & services** and asks
you to pair again.

To control more than one box, add the integration once per box.

## Entities and Services

Each box shows up as a device with:

- **`remote.<box name>`**: a remote entity for `remote.send_command`.
- **Button entities** for the common keys (arrows, OK, Guide, Menu, playback, channel, and
  volume). Number keys, color keys, and TV power/input are created disabled; enable them
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

## Examples

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

## Debugging

In your `configuration.yaml` file, add this:

```yaml
logger:
    logs:
        custom_components.xfinity_remote: debug
```

Now restart Home Assistant and do whatever isn't working.

##### Download the full logs

Note that these may contain sensitive information, so do always check before sending them to
someone. In particular, never share your token.

1. In HA, open `Settings`
2. Click `System`
3. Click `Logs`
4. Click `Download full log`

Then create an [issue](https://github.com/JeffSteinbok/hass-xfinityremote/issues) with the
lines related to `xfinity_remote` and what you were trying to do.

## How It Works

The integration talks to the same endpoints the web remote at remote.xfinity.com uses:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/pairing/start`, `/pairing/confirm` | EasyPair code and polling |
| `POST /api/v1/auth/token/refresh` | Token renewal |
| `POST /api/v1/devices` | Box name lookup |
| `POST /api/v1/processKey` `{vcode}` | Box key presses |
| `POST /api/v1/processCecKey` `{key, value}` | TV keys over HDMI-CEC |
| `POST /api/v1/text` `{cmd, arToken}` | Voice-style text commands |

## Contributing

I'm always happy to have people add features via Pull Request. To set up a dev environment
and run the tests:

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.test.txt pylint
.venv/bin/pytest
```
