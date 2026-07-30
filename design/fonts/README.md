# Display Font Notes

The profile hero is designed for Playfair Display SemiBold at weight `600`.

The repository is intentionally buildable without a vendored font binary. When
`design/fonts/PlayfairDisplay-SemiBold.ttf` is absent, the build falls back to
the serif stack defined in `design/tokens.yml`.

When the font file is present and custom fonts are enabled, the build subsets
the required glyphs and embeds the resulting WOFF2 payload directly into the
generated hero SVG files. GitHub visitors do not make any runtime request to
Google Fonts or another CDN.

To acquire the exact source used by the build, run:

```bash
python scripts/acquire_font.py
```

That script:

1. Downloads the official Playfair Display variable font from the Google Fonts
   repository pinned to commit `1e1aa08e994ff7db50116e86ccc7b52a4e4ae5b8`.
2. Verifies the source SHA-256 checksum:
   `c40f2293766a503bc70cce9e512ef844a4ccb7cbcde792fe2ea31d191917d8d6`
3. Instantiates the static `wght=600` face.
4. Writes `design/fonts/PlayfairDisplay-SemiBold.ttf`.
5. Downloads and verifies the license text SHA-256 checksum:
   `566be814f8e96e93dfa16101331557eb6b5467e9e03f627c0910fe93ca12300e`
6. Writes `design/fonts/OFL.txt`.
