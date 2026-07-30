from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import TEMPLATE_DIR


def build_markdown_renderer() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": True, "linkify": True})


def rewrite_pictures_for_theme(html_fragment: str, theme: str, mobile_breakpoint: int) -> str:
    if theme == "system":
        return html_fragment

    soup = BeautifulSoup(html_fragment, "html.parser")
    for picture in soup.find_all("picture"):
        img = picture.find("img")
        if img is None:
            continue

        mobile_src = ""
        desktop_src = img.get("src", "")
        for source in picture.find_all("source"):
            srcset = source.get("srcset", "")
            if f"-mobile-{theme}.svg" in srcset:
                mobile_src = srcset
            if f"-{theme}.svg" in srcset and "-mobile-" not in srcset:
                desktop_src = srcset

        for source in picture.find_all("source"):
            source.decompose()

        if mobile_src:
            source = soup.new_tag("source")
            source["media"] = f"(max-width: {mobile_breakpoint}px)"
            source["srcset"] = mobile_src
            picture.insert(0, source)

        img["src"] = desktop_src

    return str(soup)


def render_preview_documents(readme_markdown: str, tokens: dict) -> dict[str, str]:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("preview-readme.html.j2")

    renderer = build_markdown_renderer()
    base_html = renderer.render(readme_markdown)
    breakpoint = int(tokens["meta"]["mobile_breakpoint"])
    preview_desktop_width = int(tokens["meta"]["preview_desktop_width"])

    documents = {}
    for theme in ("light", "dark", "system"):
        themed_fragment = rewrite_pictures_for_theme(base_html, theme, breakpoint)
        documents[theme] = template.render(
            theme=theme,
            readme_html=themed_fragment,
            preview_desktop_width=preview_desktop_width,
        )
    return documents
