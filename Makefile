PYTHON ?= python
BASE ?= data/input/analysis_panel_clean_1990_2024.csv
OUT ?= data
START ?= 1990
END ?= 2024

.PHONY: install smoke build-offline build-online test clean

install:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .[dev]

smoke:
	$(PYTHON) -m gender_quota_panel.build_panel --base $(BASE) --start $(START) --end $(END) --out $(OUT) --offline

build-offline:
	$(PYTHON) -m gender_quota_panel.build_panel --base $(BASE) --start $(START) --end $(END) --out $(OUT) --offline

build-online:
	$(PYTHON) -m gender_quota_panel.build_panel --base $(BASE) --start $(START) --end $(END) --out $(OUT) --fetch-idea --download-worldbank --download-wgi --download-fsi

test:
	pytest -q

clean:
	rm -rf data/derived/* data/raw/* .pytest_cache
	touch data/derived/.gitkeep data/raw/.gitkeep
