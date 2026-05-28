# Quota Strength Step 1 Data Dictionary

## Output file
`data/derived/quota_strength_panel_1990_2024.csv`

## Backbone fields (from base panel, unchanged)
- `iso3c`: ISO-3 country code from base panel.
- `country_name`: country name from base panel.
- `year`: calendar year from base panel (1990–2024).

## New step-1 quota fields
- `has_any_quota` (0/1)
  - 1 if any quota type is present.
  - 0 if no quota type is present.

- `quota_strength_ordinal` (0/1/2/3)
  - 0 = No quota
  - 1 = Voluntary Political Party Quotas
  - 2 = Legislated Candidate Quotas
  - 3 = Reserved Seats Quotas
  - If multiple types coexist, takes the highest intensity.

- `quota_voluntary_party` (0/1)
  - Component flag for voluntary party quota.

- `quota_legislated_candidate` (0/1)
  - Component flag for legislated candidate quota.

- `quota_reserved_seats` (0/1)
  - Component flag for reserved seats quota.

- `quota_temporal_basis` (string)
  - `current_snapshot_only`: classification sourced from current-type export without historical start/end-year fields.
  - `not_in_quota_export`: no reliable match found in selected export.

- `quota_source_file` (string)
  - Source file used for this assignment (here: `export_table.csv`).

- `quota_match_status` (string)
  - `matched`: matched with high confidence (iso3 exact).
  - `manual_review_needed`: unresolved/ambiguous match requiring human review.
  - `not_matched`: no match found.

- `quota_notes` (string)
  - Audit note clarifying snapshot limitation or unmatched status.

## Intermediate audit files
- `data/interim/idea_quota_country_classification.csv`: country-level quota type extraction and classification.
- `data/interim/idea_country_match_audit.csv`: per-country matching method/score/review flags.
- `data/manual/idea_country_manual_match_needed.csv`: unresolved cases queued for manual harmonization.

## Important caveat
Step 1 is a traceable baseline and **not** final historical event coding. Countries with `current_snapshot_only` must not be interpreted as having unchanged quota status for every year from 1990 to 2024.
