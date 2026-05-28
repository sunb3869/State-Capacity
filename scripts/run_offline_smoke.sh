#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e .[dev]
pytest -q
python -m gender_quota_panel.build_panel \
  --base data/input/analysis_panel_clean_1990_2024.csv \
  --out data \
  --offline
