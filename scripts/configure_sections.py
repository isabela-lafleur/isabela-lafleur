from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sections import (
    NUMBERED_WIDGETS,
    SECTION_CONFIG_PATH,
    SECTION_ORDER,
    enabled_readme_sections,
    load_section_config,
    normalize_section_key,
    numbered_section_labels,
    write_section_config,
)


def _set_values(config: dict[str, bool], keys: list[str], value: bool) -> None:
    for key in keys:
        normalized = normalize_section_key(key)
        if normalized not in config:
            valid = ", ".join(SECTION_ORDER)
            raise ValueError(f"Unknown section: {key}. Valid sections: {valid}")
        config[normalized] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable or disable generated README sections.")
    parser.add_argument("--enable", action="append", default=[], metavar="SECTION", help="Enable a section.")
    parser.add_argument("--disable", action="append", default=[], metavar="SECTION", help="Disable a section.")
    parser.add_argument("--reset", action="store_true", help="Reset all sections to enabled.")
    parser.add_argument("--show", action="store_true", help="Print the current section config.")
    args = parser.parse_args()

    config = load_section_config()
    if args.reset:
        config = {key: True for key in SECTION_ORDER}

    if args.enable:
        _set_values(config, args.enable, True)
    if args.disable:
        _set_values(config, args.disable, False)

    if args.reset or args.enable or args.disable:
        write_section_config(config)

    if args.show or not (args.reset or args.enable or args.disable):
        labels = numbered_section_labels(config)
        print(f"Section config: {SECTION_CONFIG_PATH}")
        for key in SECTION_ORDER:
            state = "enabled" if config.get(key, False) else "disabled"
            suffix = f" -> {labels[key]}" if key in NUMBERED_WIDGETS and config.get(key, False) else ""
            print(f"  {key}: {state}{suffix}")
        print("Visible README order:", ", ".join(enabled_readme_sections(config)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
