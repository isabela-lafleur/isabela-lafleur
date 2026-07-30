# Profile Maintenance

This profile is generated from editable source files. Update the inputs, then rebuild; do not hand-edit files in `assets/generated/`.

## Font flow

1. Acquire the source font locally with `python3 scripts/acquire_font.py`.
2. Build the profile with `python3 scripts/build_profile.py`.
3. During the build, the installed Playfair Display SemiBold source is subsetted to only the characters needed by the hero.
4. That subset is embedded directly into the generated hero SVGs as a base64 WOFF2 payload.

Visitors do not make a runtime request to Google Fonts, a CDN, or any other external font host. The required SVG namespace `http://www.w3.org/2000/svg` is part of the document format, not an external runtime dependency.

## Common commands

- Normal build: `python3 scripts/build_profile.py`
- Offline build: `python3 scripts/build_profile.py --offline`
- Fallback-only hero build: `python3 scripts/build_profile.py --offline --disable-custom-font`
- Test suite: `pytest`
- Font verification: `python3 scripts/verify_embedded_font.py`
- Local preview: `python3 scripts/serve_preview.py`

## Verification notes

- `scripts/verify_embedded_font.py` checks that normal hero SVGs contain an embedded WOFF2 payload and that the decoded bytes start with the `wOF2` signature.
- The build also generates `preview/generated/readme-light.html`, `readme-dark.html`, and `readme-system.html` from the actual `README.md` so the preview uses real generated content rather than a hand-copied mockup.
- The preview page at `/preview/` is useful for checking light, dark, system, desktop, and mobile rendering before pushing, but it is only an approximation of GitHub image rendering.
- The closest real-world verification still comes from pushing generated assets to GitHub and viewing the profile there.
