# Offline Source Collection Guide for Country-by-Country Quota Coding

When Codex cannot access official websites, collect source files manually and upload them into:

- `data/sources/raw/<ISO3C>/`

Recommended naming:
- `data/sources/raw/ARG/idea_country_page_YYYYMMDD.html`
- `data/sources/raw/ARG/electoral_law_YYYYMMDD.pdf`
- `data/sources/raw/ARG/constitution_YYYYMMDD.pdf`
- `data/sources/raw/ARG/election_commission_rules_YYYYMMDD.pdf`

## Minimum source package per country (priority order)
1. International IDEA/IPU/Stockholm Gender Quotas Database country page.
2. Official constitution text (or official constitutional amendment notice).
3. Official electoral law / party law / quota law text.
4. Election commission candidate-registration rules and sanctions.
5. Official parliament or government gazette publication page for enactment and effective dates.
6. Optional cross-check: IPU or World Bank women-in-parliament series.

## Evidence extraction requirements (for every interval row)
Each row in `data/manual/quota_events_manual.csv` must include:
- `source_url`
- `source_quote`
- `source_type`
- `confidence`
- `notes`

Any record missing these fields is **not eligible** for the official manual event file.

## Coding workflow under offline-source mode
1. Upload source files into `data/sources/raw/<ISO3C>/`.
2. Copy key passages into `source_quote` with legal date/effect language.
3. Enter legal URL or archival file pointer in `source_url`.
4. Assign `confidence` using `docs/coding_protocol.md` definitions.
5. Run:
   - `python -m pip install -e .[dev]`
   - `pytest -q`
   - `python -m gender_quota_panel.build_panel --base data/input/analysis_panel_clean_1990_2024.csv --out data --offline`
