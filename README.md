# Gender Quota Panel Builder

This repository is designed for **Codex Web + GitHub**. It builds a 1990-2024 country-year panel of gender quota institutions aligned to your existing base panel:

```text
data/input/analysis_panel_clean_1990_2024.csv
```

The base panel is already included in this repository package. The output keeps the same `iso3c-country_name-year` skeleton so that later merges remain stable.

## 1. Fast run in Codex / GitHub Codespaces

```bash
python -m pip install -e .[dev]
python -m gender_quota_panel.build_panel \
  --base data/input/analysis_panel_clean_1990_2024.csv \
  --out data \
  --offline
```

Expected output:

```text
data/derived/master_gender_quota_panel_1990_2024.csv
data/derived/codebook_quota_panel.md
data/derived/diagnostics_quota_strength_by_year.csv
```

The offline run does not download anything. It is meant to verify that the repository, package, base panel, and manual-event schema all run correctly.

## 2. Full online run

```bash
python -m pip install -e .[dev]
python -m gender_quota_panel.build_panel \
  --base data/input/analysis_panel_clean_1990_2024.csv \
  --out data \
  --fetch-idea \
  --download-worldbank \
  --download-wgi \
  --download-fsi
```

Optional V-Dem file:

```bash
python -m gender_quota_panel.build_panel \
  --base data/input/analysis_panel_clean_1990_2024.csv \
  --out data \
  --fetch-idea \
  --download-worldbank \
  --download-wgi \
  --download-fsi \
  --vdem data/raw/V-Dem-CY-Core-v16.csv.zip
```

## 3. Core workflow

This project separates **standard classification** from **historical coding**.

The IDEA/IPU/Stockholm database is used for standard quota categories and current country-page information. Because historical start/end years and enforcement details must be verified against country legal sources, the repository uses a manual event file:

```text
data/manual/quota_events_manual.csv
```

Each row is one verified quota-rule interval. If a country has two active quota types in the same years, enter two rows; the script aggregates them to the country-year level.

After editing `data/manual/quota_events_manual.csv`, rerun the build command. The main output will update automatically.

## 4. Quota variables

Main ordinal variable:

| value | type | Chinese label |
|---:|---|---|
| 0 | No quota | 无配额 |
| 1 | Voluntary Political Party Quotas | 自愿性政党配额 |
| 2 | Legislated Candidate Quotas | 法定候选人配额 |
| 3 | Reserved Seats Quotas | 预留座位配额 |

Enforcement components:

- `has_any_sanction`
- `sanction_reject_list`
- `sanction_financial`
- `sanction_other`
- `placement_mandate`
- `rank_order_zipper`

Derived enforcement variables:

```text
quota_enforcement_score = sum of six enforcement components
quota_enforcement_index = quota_enforcement_score / 6
quota_strength_augmented = quota_strength_ordinal + 0.50 * quota_enforcement_index
```

The augmented variable is intended as a robustness/intensity measure. The main model should preserve the IDEA standard ordinal classification and the separate enforcement components.

## 5. Target-stage variables

```text
0 = none
1 = party candidate selection
2 = candidate nomination / candidate list
3 = seat allocation / elected seats
```

Authority variables:

```text
0 = none
1 = party statute/internal rule
2 = national or subnational ordinary law / electoral law
3 = constitutional provision
```

## 6. State capacity and mechanism variables

The script constructs:

```text
control_capacity_index = normalized state capacity * (1 - normalized democracy)
inclusive_capacity_index = normalized state capacity * normalized democracy
```

State capacity is taken from WGI Government Effectiveness when downloaded; otherwise the script falls back to the state-capacity variables already present in the base panel. Democracy is taken from V-Dem if supplied; otherwise the script falls back to `ctrl_democracy_vdem` already present in the base panel; then to WGI Voice and Accountability if downloaded.

The script also creates:

```text
seat_redistribution_cost_observed
```

This is an observed proxy based on majoritarian/single-member system, national scope, seat-result target stage, and whether a constitutional amendment was required.

## 7. Tests and GitHub Actions

Run:

```bash
pytest -q
```

A GitHub Actions workflow is included at:

```text
.github/workflows/smoke-test.yml
```

It installs the package, runs tests, and executes the offline build.

## 8. Suggested Codex first prompt

After connecting Codex to this GitHub repository, use:

```text
Please inspect this repository. Run `python -m pip install -e .[dev]`, then run `pytest -q`, then run the offline build command from README. After confirming the project runs, help me fill `data/manual/quota_events_manual.csv` country by country using the IDEA/IPU/Stockholm gender quota database plus official parliament, election commission, and legal sources. Keep `iso3c-country_name-year` consistent with `data/input/analysis_panel_clean_1990_2024.csv`. Do not overwrite the base panel. Add sources, quotes, confidence, and notes for every manually coded quota interval.
```
