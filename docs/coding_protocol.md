# Coding Protocol

## 1. Unit of observation
Country-year, 1990-2024.

## 2. Event file logic
`data/manual/quota_events_manual.csv` is event-interval based. A rule active from 2003 through 2024 is coded as one row with `start_year=2003`, `end_year=2024` or blank `end_year`.

If a country has both a voluntary party quota and a legal candidate quota at the same time, enter two rows. The script will aggregate them and use the highest ordinal quota strength while preserving type flags.

## 3. Quota type coding
- `no_quota`: no national legal quota and no major voluntary party quota verified.
- `voluntary_party`: party-internal rule or commitment, not imposed by state law.
- `legislated_candidate`: candidate quota imposed by constitution, electoral law, party law, or other binding public law.
- `reserved_seats`: seats in the elected chamber are reserved or guaranteed for women.

## 4. Enforcement coding
Code every component separately:

| variable | meaning |
|---|---|
| `has_any_sanction` | any penalty for non-compliance |
| `sanction_reject_list` | electoral authority refuses non-compliant candidate list |
| `sanction_financial` | public funding loss, fine, or other monetary penalty |
| `sanction_other` | non-financial/non-rejection penalty |
| `placement_mandate` | law/rule specifies candidate placement/rank order |
| `rank_order_zipper` | alternating women/men or zipper-style ranking rule |

## 5. Target stage coding
- `party_candidate_selection`: party rules shape internal recruitment or candidate selection.
- `candidate_nomination`: the legal nomination list must meet a quota.
- `seat_allocation`: the elected chamber allocates/reserves seats for women.

## 6. Source hierarchy
Prefer:
1. IDEA/IPU/Stockholm country page for standardized category and summary.
2. Constitution or electoral law text.
3. Election commission manuals, decrees, or candidate-registration rules.
4. Official parliament pages.
5. Peer-reviewed or high-quality secondary source only if official text is unavailable.

## 7. Confidence coding
- `high`: official legal source confirms type, date, and enforcement.
- `medium`: IDEA plus one reliable secondary source confirms most details.
- `low`: classification likely, but date or enforcement details remain uncertain.


## 8. Quota strength and enforcement separation (required)
- `quota_strength_ordinal = 0`: No quota (no national legal quota and no major voluntary party quota).
- `quota_strength_ordinal = 1`: Voluntary Political Party Quotas.
- `quota_strength_ordinal = 2`: Legislated Candidate Quotas.
- `quota_strength_ordinal = 3`: Reserved Seats Quotas.

Do **not** let enforcement components overwrite or reorder the four-level IDEA/IPU/Stockholm classification. Enforcement is a separate dimension:
- `quota_enforcement_score = has_any_sanction + sanction_reject_list + sanction_financial + sanction_other + placement_mandate + rank_order_zipper`
- `quota_enforcement_index = quota_enforcement_score / 6`
- `quota_strength_augmented = quota_strength_ordinal + 0.50 * quota_enforcement_index`

Use `quota_strength_augmented` only for robustness/intensity analysis.

## 9. Target-stage interpretation rule
- `party_candidate_selection`: usually for voluntary party quotas.
- `candidate_nomination` / candidate list stage: usually for legislated candidate quotas.
- `seat_allocation` / elected seats: usually for reserved seats quotas.

If a legal text mixes stages, record the primary binding stage in `target_stage` and explain secondary stages in `notes`.

## 10. Source completeness gate
Rows missing any of `source_url`, `source_quote`, `source_type`, `confidence`, `notes` must not be merged into `data/manual/quota_events_manual.csv`.


## 11. Manual-event schema vs. derived country-year fields
The event file is interval-based and stores rule-level inputs. Some country-year analysis variables are derived during build and do not need manual row entry for every interval:
- Derived from `quota_type`/strength logic: `quota_strength_ordinal`, `quota_voluntary_party`, `quota_legislated_candidate`, `quota_reserved_seats`, `has_any_quota`.
- Scope harmonization: `national_or_subnational_scope` can be entered directly or mapped from `level_scope` during review.

Template files may include both raw-input and derived-tracking columns for audit convenience, but official calculations come from the build pipeline.
