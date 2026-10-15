# Security Policy

Thank you for helping keep **hass-xfinityremote** and its users safe.

This is an unofficial, community-maintained Home Assistant custom integration for
Xfinity X1 set-top boxes. It is not affiliated with or endorsed by Comcast. Please keep
that scope in mind when reporting issues: vulnerabilities in Xfinity's cloud service,
the web remote at remote.xfinity.com, or the boxes themselves should be reported
directly to Comcast.

## Supported Versions

Security fixes are provided for the latest release only. Older versions are not
patched, so please update before reporting.

| Version                 | Supported          |
| ----------------------- | ------------------ |
| Latest release          | :white_check_mark: |
| Any older release       | :x:                |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**
Public issues can expose users before a fix is available.

Instead, report privately in one of these ways:

- [Report a vulnerability](https://github.com/JeffSteinbok/hass-xfinityremote/security/advisories/new)
  through GitHub's private vulnerability reporting, or
- reach out to the maintainer directly on **Discord** or **LinkedIn**; contact details
  are listed on my GitHub profile: [@JeffSteinbok](https://github.com/JeffSteinbok)

When reporting, please include as much of the following as you can:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept or logs if relevant)
- The version of the integration you're running
- Any suggested remediation, if you have one

Please **never share your Xfinity remote token** (the long string starting with `eyJ`).
Redact it, along with account and device identifiers, from any logs or diagnostics.

## What to Expect

- I'll acknowledge your report as soon as I reasonably can.
- I'll investigate and keep you updated on progress toward a fix.
- Once a fix is released, I'm happy to credit you for the discovery. Let me know if
  you'd prefer to remain anonymous.

Thanks for reporting responsibly. 🙏
