from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from PIL import Image, ImageSequence
import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import GENERATED_DATA_DIR, write_json

ARCHIVE_URL = "https://pdb101.rcsb.org/motm/motm-image-download"
ARTICLE_BASE_URL = "https://pdb101.rcsb.org"
CACHE_JSON_PATH = GENERATED_DATA_DIR / "molecule_of_the_month.json"
CACHE_PNG_PATH = GENERATED_DATA_DIR / "molecule_of_the_month.png"
MAX_PNG_WIDTH = 760
MAX_PNG_HEIGHT = 760
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class MoleculeOfMonthError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArchiveEntry:
    article_id: int
    article_url: str
    title: str
    tiff_urls: tuple[str, ...]


def current_date() -> date:
    override = os.environ.get("PROFILE_BUILD_DATE")
    if override:
        return date.fromisoformat(override)
    return date.today()


def default_cache_json_path() -> Path:
    return CACHE_JSON_PATH


def default_cache_png_path() -> Path:
    return CACHE_PNG_PATH


def load_cached_feature(
    cache_json_path: Path | None = None,
    cache_png_path: Path | None = None,
) -> dict[str, Any] | None:
    metadata_path = cache_json_path or default_cache_json_path()
    image_path = cache_png_path or default_cache_png_path()
    if not metadata_path.exists() or not image_path.exists():
        return None

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    png_bytes = image_path.read_bytes()
    cached = dict(metadata)
    cached["image_base64"] = base64.b64encode(png_bytes).decode("ascii")
    cached["image_mime"] = "image/png"
    cached["cache_png_path"] = str(image_path)
    return cached


def parse_archive_entries(html: str) -> list[ArchiveEntry]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise MoleculeOfMonthError("RCSB archive page did not include a downloadable image table.")

    month_pattern = re.compile(rf"^({'|'.join(MONTH_NAMES)})\b")
    entries: list[ArchiveEntry] = []

    for table in tables:
        current_entry: ArchiveEntry | None = None
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            row_text = " ".join(cell.get_text(" ", strip=True) for cell in cells if cell.get_text(" ", strip=True))
            if re.fullmatch(r"\d{4}", row_text):
                continue

            article_links = row.find_all("a", href=re.compile(r"^/motm/\d+$"))
            article_link = article_links[0] if article_links else None
            tiff_links = [
                urljoin(ARTICLE_BASE_URL, link["href"])
                for link in row.find_all("a", href=re.compile(r"\.tiff?$", re.IGNORECASE))
            ]
            if not article_link:
                if current_entry and tiff_links:
                    current_entry = ArchiveEntry(
                        article_id=current_entry.article_id,
                        article_url=current_entry.article_url,
                        title=current_entry.title,
                        tiff_urls=current_entry.tiff_urls + tuple(tiff_links),
                    )
                    entries[-1] = current_entry
                continue

            title_link = max(article_links, key=lambda link: len(link.get_text(" ", strip=True)))
            title = title_link.get_text(" ", strip=True)
            if not title or not month_pattern.search(row_text):
                continue

            current_entry = ArchiveEntry(
                article_id=int(article_link["href"].rstrip("/").rsplit("/", 1)[-1]),
                article_url=urljoin(ARTICLE_BASE_URL, article_link["href"]),
                title=title,
                tiff_urls=tuple(tiff_links),
            )
            entries.append(current_entry)

        if entries:
            break

    if not entries:
        raise MoleculeOfMonthError("Unable to parse any Molecule of the Month archive entries.")
    return entries


def fetch_archive_entries(session: requests.Session | None = None) -> list[ArchiveEntry]:
    active_session = session or requests.Session()
    response = active_session.get(ARCHIVE_URL, timeout=30)
    response.raise_for_status()
    return parse_archive_entries(response.text)


def select_archive_entry(entries: list[ArchiveEntry], config: dict[str, Any]) -> ArchiveEntry:
    mode = str(config.get("mode", "auto")).strip().lower()
    if mode == "auto":
        return entries[0]

    requested_id = config.get("article_id")
    if requested_id in (None, ""):
        raise MoleculeOfMonthError("hero.molecule_of_the_month.article_id is required in fixed mode.")

    for entry in entries:
        if entry.article_id == int(requested_id):
            return entry
    raise MoleculeOfMonthError(f"Could not find Molecule of the Month article {requested_id} in the archive.")


def parse_article_page(html: str, article_url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        raise MoleculeOfMonthError(f"Article page did not contain an h1 heading: {article_url}")
    raw_title = heading.get_text(" ", strip=True)
    title = re.sub(r"^Molecule of the Month:\s*", "", raw_title)

    text = soup.get_text("\n", strip=True)
    footer_pattern = re.compile(
        rf"^({'|'.join(MONTH_NAMES)})\s+(\d{{4}}),\s+(.+)$",
        re.MULTILINE,
    )
    match = footer_pattern.search(text)
    if not match:
        raise MoleculeOfMonthError(f"Could not find article date/author footer: {article_url}")

    month_year = f"{match.group(1)} {match.group(2)}"
    author = match.group(3).strip()
    return {
        "title": title,
        "month_year": month_year,
        "author": author,
        "article_url": article_url,
    }


def fetch_article_metadata(article_url: str, session: requests.Session | None = None) -> dict[str, str]:
    active_session = session or requests.Session()
    response = active_session.get(article_url, timeout=30)
    response.raise_for_status()
    return parse_article_page(response.text, article_url)


def _image_frame(image: Image.Image) -> Image.Image:
    try:
        first_frame = next(ImageSequence.Iterator(image))
    except StopIteration:
        return image.copy()
    return first_frame.copy()


def convert_tiff_to_png_payload(tiff_bytes: bytes) -> dict[str, Any]:
    with Image.open(io.BytesIO(tiff_bytes)) as source_image:
        frame = _image_frame(source_image)
        original_width, original_height = frame.size
        converted = frame.convert("RGBA")
        resized = False
        if converted.width > MAX_PNG_WIDTH or converted.height > MAX_PNG_HEIGHT:
            converted.thumbnail((MAX_PNG_WIDTH, MAX_PNG_HEIGHT), Image.Resampling.LANCZOS)
            resized = True

        png_buffer = io.BytesIO()
        converted.save(png_buffer, format="PNG", optimize=True)
        png_bytes = png_buffer.getvalue()

    return {
        "png_bytes": png_bytes,
        "original_width": int(original_width),
        "original_height": int(original_height),
        "png_width": int(converted.width),
        "png_height": int(converted.height),
        "resized": resized,
        "cropped": False,
    }


def select_tiff_url(entry: ArchiveEntry, config: dict[str, Any]) -> str:
    requested_name = str(config.get("image_name", "")).strip()
    if requested_name:
        for url in entry.tiff_urls:
            if Path(url).name == requested_name:
                return url
        raise MoleculeOfMonthError(
            f"Configured image_name {requested_name!r} was not found for article {entry.article_id}."
        )

    if not entry.tiff_urls:
        raise MoleculeOfMonthError(f"Archive entry {entry.article_id} did not expose any TIFF images.")
    return entry.tiff_urls[0]


def _resize_note(resized: bool, cropped: bool) -> str:
    if resized and cropped:
        return "Image cropped and resized from the original TIFF."
    if cropped:
        return "Image cropped from the original TIFF."
    if resized:
        return "Image resized from the original TIFF."
    return "Image used from the original TIFF without cropping."


def write_cache_files(
    payload: dict[str, Any],
    cache_json_path: Path | None = None,
    cache_png_path: Path | None = None,
) -> None:
    metadata_path = cache_json_path or default_cache_json_path()
    image_path = cache_png_path or default_cache_png_path()
    metadata = dict(payload)
    png_bytes = metadata.pop("png_bytes")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(png_bytes)
    write_json(metadata_path, metadata)


def fetch_and_cache_molecule_of_the_month(
    config: dict[str, Any],
    *,
    session: requests.Session | None = None,
    cache_json_path: Path | None = None,
    cache_png_path: Path | None = None,
) -> dict[str, Any]:
    active_session = session or requests.Session()
    entries = fetch_archive_entries(active_session)
    entry = select_archive_entry(entries, config)
    article = fetch_article_metadata(entry.article_url, active_session)

    attempted_urls: list[str] = []
    candidate_urls = list(entry.tiff_urls)
    preferred_url = select_tiff_url(entry, config)
    if preferred_url in candidate_urls:
        candidate_urls.remove(preferred_url)
    candidate_urls.insert(0, preferred_url)

    last_error: Exception | None = None
    for image_url in candidate_urls:
        attempted_urls.append(image_url)
        try:
            response = active_session.get(image_url, timeout=45)
            response.raise_for_status()
            image_payload = convert_tiff_to_png_payload(response.content)
            feature = {
                "article_id": entry.article_id,
                "article_url": article["article_url"],
                "title": article["title"],
                "month_year": article["month_year"],
                "author": article["author"],
                "label": "Molecule of the Month",
                "link_label": "Original article",
                "link_host_label": article["article_url"].replace("https://", "").replace("http://", ""),
                "license": "CC BY 4.0",
                "license_owner": "RCSB PDB",
                "image_url": image_url,
                "image_name": Path(image_url).name,
                "image_width": image_payload["png_width"],
                "image_height": image_payload["png_height"],
                "original_width": image_payload["original_width"],
                "original_height": image_payload["original_height"],
                "image_resized": image_payload["resized"],
                "image_cropped": image_payload["cropped"],
                "image_transform_note": _resize_note(image_payload["resized"], image_payload["cropped"]),
                "source": "live",
                "cached_on": current_date().isoformat(),
                "png_bytes": image_payload["png_bytes"],
            }
            write_cache_files(feature, cache_json_path=cache_json_path, cache_png_path=cache_png_path)
            live_result = load_cached_feature(cache_json_path=cache_json_path, cache_png_path=cache_png_path)
            if live_result is None:
                raise MoleculeOfMonthError("Molecule of the Month cache write did not produce a readable cache.")
            live_result["source"] = "live"
            return live_result
        except Exception as exc:  # pragma: no cover - exercised indirectly by fallback behavior
            last_error = exc
            continue

    attempted = ", ".join(attempted_urls) or "no image URLs"
    raise MoleculeOfMonthError(
        f"Unable to download or convert a suitable TIFF for article {entry.article_id}. "
        f"Attempted: {attempted}."
    ) from last_error


def fetch_molecule_of_the_month(
    config: dict[str, Any] | None,
    *,
    offline: bool = False,
    session: requests.Session | None = None,
    cache_json_path: Path | None = None,
    cache_png_path: Path | None = None,
) -> dict[str, Any]:
    active_config = dict(config or {})
    mode = str(active_config.get("mode", "auto")).strip().lower() or "auto"
    active_config["mode"] = mode

    cached = load_cached_feature(cache_json_path=cache_json_path, cache_png_path=cache_png_path)
    if offline:
        if cached is None:
            raise MoleculeOfMonthError("Offline build requested, but no Molecule of the Month cache is available.")
        if mode == "fixed" and active_config.get("article_id") not in (None, ""):
            requested_id = int(active_config["article_id"])
            if int(cached.get("article_id", -1)) != requested_id:
                raise MoleculeOfMonthError(
                    f"Offline cache contains article {cached.get('article_id')}, not requested article {requested_id}."
                )
        cached["source"] = "cache"
        return cached

    try:
        return fetch_and_cache_molecule_of_the_month(
            active_config,
            session=session,
            cache_json_path=cache_json_path,
            cache_png_path=cache_png_path,
        )
    except Exception:
        if cached is None:
            raise
        if mode == "fixed" and active_config.get("article_id") not in (None, ""):
            requested_id = int(active_config["article_id"])
            if int(cached.get("article_id", -1)) != requested_id:
                raise
        cached["source"] = "cache"
        return cached


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and cache the latest RCSB PDB-101 Molecule of the Month feature.")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--mode", choices=("auto", "fixed"), default="auto")
    parser.add_argument("--article-id", type=int, default=None)
    parser.add_argument("--image-name", default="")
    args = parser.parse_args()

    config = {
        "mode": args.mode,
        "article_id": args.article_id,
        "image_name": args.image_name,
    }
    feature = fetch_molecule_of_the_month(config, offline=args.offline)
    printable = dict(feature)
    printable.pop("image_base64", None)
    printable.pop("cache_png_path", None)
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
