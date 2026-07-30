build:
	python3 scripts/build_profile.py

offline:
	python3 scripts/build_profile.py --offline

fallback-font:
	python3 scripts/build_profile.py --offline --disable-custom-font

test:
	pytest

verify-font:
	python3 scripts/verify_embedded_font.py

preview:
	python3 scripts/serve_preview.py

check:
	python3 scripts/build_profile.py --offline
	pytest
	python3 scripts/verify_embedded_font.py
