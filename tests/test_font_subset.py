from __future__ import annotations

from pathlib import Path

import pytest

from scripts.subset_font import build_font_face_css, collect_charset, encode_embedded_font, subset_font_to_base64


def test_charset_includes_safety_and_special_characters() -> None:
    charset = collect_charset(["Isabela LaFleur", "Signal / Noise"])
    assert "I" in charset
    assert "/" in charset
    assert "—" in charset


def test_fallback_mode_succeeds_without_font() -> None:
    assert subset_font_to_base64(["Isabela LaFleur"], disable_custom_font=True) is None
    assert build_font_face_css(None) == ""


def test_invalid_subset_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="valid WOFF2"):
        encode_embedded_font(b"not-a-woff2", disabled=False)


@pytest.mark.skipif(
    not Path("design/fonts/PlayfairDisplay-SemiBold.ttf").exists(),
    reason="Vendored display font is optional.",
)
def test_font_subset_is_embedded_as_woff2_when_font_exists() -> None:
    encoded = subset_font_to_base64(["Isabela LaFleur"])
    assert encoded is not None
    css = build_font_face_css(encoded)
    assert "data:font/woff2;base64," in css
    assert "http://" not in css
    assert "https://" not in css
