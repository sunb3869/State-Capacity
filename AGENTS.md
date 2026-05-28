# Codex instructions for this repository

## Project purpose
Build a country-year database of gender quota institutions from 1990 to 2024, aligned to `data/input/analysis_panel_clean_1990_2024.csv`.

## Non-negotiable standards
1. Do not change `iso3c`, `country_name`, or `year` in the base panel.
2. Do not overwrite `data/input/analysis_panel_clean_1990_2024.csv`.
3. Treat `data/manual/quota_events_manual.csv` as the authoritative hand-coded event file.
4. Use the International IDEA/IPU/Stockholm Global Database of Gender Quotas as the standard classification source.
5. For historical years, verify start/end dates and enforcement details with official parliament, election commission, constitutional, electoral-law, or government legal sources when possible.
6. Every manually coded event row must include `source_url`, `source_quote`, `source_type`, `confidence`, and `notes`.
7. Keep the main ordinal classification separate from enforcement components.
8. Use `quota_strength_augmented` only as a robustness/intensity measure.

## Commands to run before proposing changes
```bash
python -m pip install -e .[dev]
pytest -q
python -m gender_quota_panel.build_panel --base data/input/analysis_panel_clean_1990_2024.csv --out data --offline
```

## Manual event coding schema
Each row in `data/manual/quota_events_manual.csv` is one country-rule interval:
- `iso3c`, `country_name`
- `start_year`, `end_year`
- `quota_type`: `voluntary_party`, `legislated_candidate`, `reserved_seats`, or `no_quota`
- `target_stage`: `party_candidate_selection`, `candidate_nomination`, or `seat_allocation`
- `mandating_authority`: `party_statute`, `national_law`, `subnational_law`, or `constitution`
- enforcement variables: `has_any_sanction`, `sanction_reject_list`, `sanction_financial`, `sanction_other`, `placement_mandate`, `rank_order_zipper`
- `requires_constitutional_amendment`
- evidence fields: `legal_basis`, `source_url`, `source_quote`, `source_type`, `coder`, `confidence`, `notes`

## Research logic
The dataset supports a theory in which quota adoption varies by state capacity form:
- control-type capacity: classification, directed integration, controlled distribution of representation;
- inclusive-type capacity: unified citizenship, competitive absorption, procedural integration.

The empirical design should preserve these distinctions rather than collapsing all quotas into a binary variable.
