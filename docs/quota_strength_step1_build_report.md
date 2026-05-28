# Quota Strength Step 1 Build Report

## Scope
This step builds a **baseline quota-strength panel** using only:
- Base skeleton: `data/input/analysis_panel_clean_1990_2024.csv`
- IDEA/IPU/Stockholm Gender Quotas Database export files under `data/input/`

Excluded in this step: enforcement strength, quota target stage coding, Parline time series integration, FSI, WGI, V-Dem, CCP, UCDP, state-capacity variables, and seat reallocation cost variables.

## Input file audit
- Checked `data/input/export_table.xls` (not present in repository).
- Checked `data/input/export_table.csv` (selected source).
- Checked `data/input/csv.csv` and `data/input/csv-2.csv` (identified as Parline data exports, not quota classification exports).

### Why `export_table.csv` was selected
`export_table.csv` includes fields with explicit Gender Quotas Database structure, including:
- `Country`, `ISO3`
- `Single/Lower House>Quota type`
- `General>Voluntary political party quotas`
and additional quota-relevant fields for legal basis/sanctions.

`csv.csv` and `csv-2.csv` are labeled as Parline data explorer outputs and were not used.

## Variable construction rules
### Core outputs
- `has_any_quota` = 1 when any of the three quota flags is 1; else 0.
- `quota_strength_ordinal`:
  - 0 = no quota
  - 1 = voluntary political party quota
  - 2 = legislated candidate quota
  - 3 = reserved seats quota

### Composite regimes
When multiple types coexist in a country, the highest-intensity type is retained in `quota_strength_ordinal`, while all component flags are preserved:
- `quota_voluntary_party`
- `quota_legislated_candidate`
- `quota_reserved_seats`

## Country matching workflow
- Primary key matching used `iso3c` (base) ↔ `ISO3` (IDEA export).
- Name similarity metrics recorded for audit only.
- Unmatched or low-certainty matches were sent to manual review, not forced.

## Temporal-basis handling
No explicit historical start/end-year fields were detected in the selected quota export.
Therefore, the country classification is treated as **current snapshot evidence** and not as historical event timing.
- Matched countries: `quota_temporal_basis = current_snapshot_only`
- Unmatched countries: `quota_temporal_basis = not_in_quota_export`

## Outputs generated
1. `data/interim/idea_quota_country_classification.csv`
2. `data/interim/idea_country_match_audit.csv`
3. `data/manual/idea_country_manual_match_needed.csv`
4. `data/derived/quota_strength_panel_1990_2024.csv`
5. `docs/quota_strength_step1_build_report.md` (this file)
6. `docs/quota_strength_step1_data_dictionary.md`

## Quality checks
- Base panel overwrite check: no overwrite performed.
- Panel row equality: 6334 vs base 6334 (pass).
- Key triplet alignment (`iso3c`, `country_name`, `year`) preserved row-by-row (pass).
- `quota_strength_ordinal` domain restricted to 0/1/2/3 (pass).
- `has_any_quota` consistency with strength (pass).
- Multi-type logic uses max-intensity + preserved component flags (pass).
- No undocumented backfill to 1990 from current status: all matched countries marked `current_snapshot_only`.

## Descriptive results
- Rows: 6334
- Countries: 181
- Year range: 1990–2024
- Countries with any quota: 116
- Countries with no quota: 65
- Countries needing manual match review: 60
- Countries coded from current snapshot only: 121

### Country counts by `quota_strength_ordinal`
- 0 (No quota): 65
- 1 (Voluntary party): 33
- 2 (Legislated candidate): 63
- 3 (Reserved seats): 20

## Legacy variable comparison (for reference only)
Existing base variables `quota_adopted_this_year` and `quota_strength_3cat` were not modified.
This step does not replace historical event coding and should be treated as a documented first-pass snapshot-aligned panel.

## Names requiring manual review
See `data/manual/idea_country_manual_match_needed.csv`.
Typical unresolved/ambiguous cases include: Afghanistan, United Arab Emirates, Democratic Republic of the Congo, German Democratic Republic, Korea naming variants, Türkiye/Turkey naming variants, and other export-name discrepancies.

## Next-step source requirements (for enforcement and target-stage)
To move to enforcement strength and target stage, supplement with:
- Official constitutional and electoral-law texts (national gazettes/parliaments/election commissions).
- Political party statutes for voluntary quotas.
- Official amendment dates and entry-into-force dates for start/end-year coding.
- Legal sanction implementation details (list rejection, financial penalties, other sanctions).
