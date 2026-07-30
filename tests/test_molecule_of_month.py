from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from scripts.fetch_molecule_of_month import (
    fetch_and_cache_molecule_of_the_month,
    fetch_molecule_of_the_month,
    parse_archive_entries,
    parse_article_page,
    write_cache_files,
)


ARCHIVE_HTML = """
<html>
  <body>
    <table>
      <tr><td>2026</td></tr>
      <tr>
        <td><a href="/motm/319">July</a></td>
        <td><a href="/motm/319">319</a></td>
        <td><a href="/motm/319">Hantavirus</a></td>
        <td><a href="https://cdn.rcsb.org/images/motm/9p3x.tif">9p3x.tif</a></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td><a href="https://cdn.rcsb.org/images/motm/9p3y.tif">9p3y.tif</a></td>
      </tr>
      <tr>
        <td><a href="/motm/318">June</a></td>
        <td><a href="/motm/318">318</a></td>
        <td><a href="/motm/318">Therapeutic Phage</a></td>
        <td><a href="https://cdn.rcsb.org/images/motm/E217.tif">E217.tif</a></td>
      </tr>
    </table>
  </body>
</html>
"""

ARTICLE_HTML = """
<html>
  <body>
    <h1>Molecule of the Month: Hantavirus</h1>
    <p>Family of rodent-borne viruses that can cause severe illness in humans</p>
    <p>July 2026, Janet Iwasa</p>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, *, text: str = "", content: bytes = b"", status_code: int = 200):
        self.text = text
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse], *, fail: bool = False):
        self.responses = responses
        self.fail = fail

    def get(self, url: str, timeout: int = 30):
        if self.fail:
            raise RuntimeError("network unavailable")
        if url not in self.responses:
            raise KeyError(url)
        return self.responses[url]


def _sample_tiff(width: int = 120, height: int = 80) -> bytes:
    image = Image.new("RGB", (width, height), color=(160, 190, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="TIFF")
    return buffer.getvalue()


def _sample_png(width: int = 120, height: int = 80) -> bytes:
    image = Image.new("RGBA", (width, height), color=(160, 190, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_parse_archive_entries_collects_grouped_tiffs() -> None:
    entries = parse_archive_entries(ARCHIVE_HTML)

    assert entries[0].article_id == 319
    assert entries[0].title == "Hantavirus"
    assert entries[0].tiff_urls == (
        "https://cdn.rcsb.org/images/motm/9p3x.tif",
        "https://cdn.rcsb.org/images/motm/9p3y.tif",
    )


def test_parse_article_page_extracts_title_month_and_author() -> None:
    parsed = parse_article_page(ARTICLE_HTML, "https://pdb101.rcsb.org/motm/319")

    assert parsed["title"] == "Hantavirus"
    assert parsed["month_year"] == "July 2026"
    assert parsed["author"] == "Janet Iwasa"


def test_fetch_and_cache_molecule_of_the_month_writes_png_cache(tmp_path: Path) -> None:
    cache_json = tmp_path / "motm.json"
    cache_png = tmp_path / "motm.png"
    session = FakeSession(
        {
            "https://pdb101.rcsb.org/motm/motm-image-download": FakeResponse(text=ARCHIVE_HTML),
            "https://pdb101.rcsb.org/motm/319": FakeResponse(text=ARTICLE_HTML),
            "https://cdn.rcsb.org/images/motm/9p3x.tif": FakeResponse(content=_sample_tiff()),
        }
    )

    result = fetch_and_cache_molecule_of_the_month(
        {"mode": "auto"},
        session=session,
        cache_json_path=cache_json,
        cache_png_path=cache_png,
    )

    assert result["article_id"] == 319
    assert result["title"] == "Hantavirus"
    assert result["image_width"] == 120
    assert result["image_height"] == 80
    assert result["source"] == "live"
    assert cache_json.exists()
    assert cache_png.exists()


def test_fetch_molecule_of_the_month_falls_back_to_cache(tmp_path: Path) -> None:
    cache_json = tmp_path / "motm.json"
    cache_png = tmp_path / "motm.png"
    write_cache_files(
        {
            "article_id": 319,
            "article_url": "https://pdb101.rcsb.org/motm/319",
            "title": "Hantavirus",
            "month_year": "July 2026",
            "author": "Janet Iwasa",
            "label": "Molecule of the Month",
            "link_label": "Original article",
            "link_host_label": "pdb101.rcsb.org/motm/319",
            "license": "CC BY 4.0",
            "license_owner": "RCSB PDB",
            "image_url": "https://cdn.rcsb.org/images/motm/9p3x.tif",
            "image_name": "9p3x.tif",
            "image_width": 120,
            "image_height": 80,
            "original_width": 120,
            "original_height": 80,
            "image_resized": False,
            "image_cropped": False,
            "image_transform_note": "Image used from the original TIFF without cropping.",
            "source": "live",
            "cached_on": "2026-07-30",
            "png_bytes": _sample_png(),
        },
        cache_json_path=cache_json,
        cache_png_path=cache_png,
    )

    fallback = fetch_molecule_of_the_month(
        {"mode": "auto"},
        session=FakeSession({}, fail=True),
        cache_json_path=cache_json,
        cache_png_path=cache_png,
    )

    assert fallback["source"] == "cache"
    assert fallback["article_id"] == 319
    assert fallback["image_base64"]
