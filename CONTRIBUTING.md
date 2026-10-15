# Contributing

Pull requests are welcome. For anything bigger than a small fix, please open an
[issue](https://github.com/JeffSteinbok/hass-xfinityremote/issues/new/choose) first so we
can agree on the approach.

## Development setup

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.test.txt pylint
.venv/bin/pytest
.venv/bin/pylint --recursive=yes --disable=W,C,R custom_components tests
```

CI runs the same pytest and pylint checks on every pull request, plus the
[HACS](https://hacs.xyz/docs/publish/action) and
[hassfest](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) validators.

## Code layout

| Path | What it is |
|---|---|
| `custom_components/xfinity_remote/api.py` | Async client for the remote.xfinity.com API. No Home Assistant imports, so it can be tested on its own. |
| `custom_components/xfinity_remote/config_flow.py` | EasyPair and paste-a-token setup, plus reauth. |
| `custom_components/xfinity_remote/__init__.py` | Setup and the periodic token refresh. |
| `custom_components/xfinity_remote/entity.py` | Shared device info and error handling (refresh-and-retry before reauth). |
| `custom_components/xfinity_remote/remote.py`, `button.py` | The entities. |
| `custom_components/xfinity_remote/diagnostics.py` | Diagnostics download, with the token and identifiers redacted. |
| `tests/` | pytest suite; the API is mocked with `aioresponses`, and the integration with `pytest-homeassistant-custom-component`. |

## Working with the Xfinity API

The API is unofficial and was reverse-engineered from remote.xfinity.com. The quickest
way to see what a button does is to open the web remote with your browser's developer
tools on the **Network** tab and press it.

- **Never commit a real token, account ID, or device ID**, not even in a test fixture.
  `tests/conftest.py` has `make_token()` for building fake tokens.
- Redact the same values from anything you paste into an issue or pull request.

## Testing against a real box

Copy the integration into your Home Assistant config and restart:

```bash
rsync -rltvz --delete --no-perms --no-owner \
  --exclude='__pycache__' --exclude='.*' \
  custom_components/xfinity_remote/ <ssh-user>@homeassistant.local:/config/custom_components/xfinity_remote/
```

Then turn on debug logging (see [Debugging](README.md#debugging)).

## Releasing (maintainers)

1. Merge to `main`.
2. Run **Actions → Release Automation → Run workflow** with `patch`, `minor`, or `major`.
   It runs the tests, bumps the version in `manifest.json`, pushes the commit and tag,
   and creates a **draft** release.
3. Add release notes to the draft and **publish** it. HACS ignores draft releases.

The workflow pushes with the `PAT_TOKEN` repository secret: a fine-grained token scoped to
this repository with **Contents: Read and write**. When it expires, the workflow fails at
checkout; create a new one and update the secret.
