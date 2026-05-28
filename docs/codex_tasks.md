# Suggested Codex task sequence

## Task 1: Verify repo health
Run tests and offline build. Confirm the output row count equals the base panel row count.

## Task 2: Generate IDEA current template
Run the online build with `--fetch-idea`. Inspect `data/derived/idea_current_country_summary.csv` and `data/manual/quota_events_template.csv`.

## Task 3: Country-by-country manual coding
For each country with a current or historical quota, fill `data/manual/quota_events_manual.csv`.

For each row, record:
- quota type;
- start/end year;
- target stage;
- authority level;
- enforcement components;
- whether constitutional amendment was required;
- official legal basis and source quote.

## Task 4: Build panel and diagnostics
Run the full build. Inspect:
- `data/derived/master_gender_quota_panel_1990_2024.csv`
- `data/derived/diagnostics_quota_strength_by_year.csv`
- `data/derived/codebook_quota_panel.md`

## Task 5: Add model-ready scripts
After the manual event file is stable, add scripts for:
- event-history models of first quota adoption;
- ordered logit/probit for quota strength;
- interaction models for control-type and inclusive-type state capacity;
- robustness checks using `quota_strength_augmented`.
