from __future__ import annotations

EVENT_SCHEMA = [
    "iso3c", "country_name", "start_year", "end_year",
    "quota_type", "quota_strength_base", "target_stage", "target_stage_score",
    "mandating_authority", "mandating_authority_level",
    "level_scope", "lower_house_scope", "upper_house_scope", "subnational_scope",
    "quota_target_percent", "reserved_seats_number",
    "has_any_sanction", "sanction_reject_list", "sanction_financial", "sanction_other",
    "placement_mandate", "rank_order_zipper", "requires_constitutional_amendment",
    "legal_basis", "source_url", "source_quote", "source_type", "coder", "confidence", "notes",
]

QUOTA_TYPE_MAP = {
    "no_quota": 0,
    "none": 0,
    "voluntary_party": 1,
    "voluntary political party quotas": 1,
    "voluntary political party quota": 1,
    "political_party_voluntary": 1,
    "legislated_candidate": 2,
    "legal_candidate": 2,
    "legal candidate quotas": 2,
    "legislated candidate quotas": 2,
    "candidate_quota_law": 2,
    "reserved_seats": 3,
    "reserved seats quotas": 3,
    "reserved seats": 3,
    "reserved_seats_quota": 3,
}

TARGET_STAGE_MAP = {
    "none": 0,
    "party_selection": 1,
    "party_candidate_selection": 1,
    "candidate_selection": 1,
    "candidate_nomination": 2,
    "candidate_list": 2,
    "candidate_lists": 2,
    "nomination": 2,
    "seat_allocation": 3,
    "elected_seats": 3,
    "reserved_seats": 3,
    "result": 3,
}

MANDATE_AUTHORITY_MAP = {
    "none": 0,
    "party": 1,
    "political_party": 1,
    "party_statute": 1,
    "party_rule": 1,
    "subnational_law": 2,
    "national_law": 2,
    "ordinary_law": 2,
    "electoral_law": 2,
    "legislation": 2,
    "law": 2,
    "constitution_or_law": 2,
    "constitution": 3,
    "constitutional": 3,
}

ENFORCEMENT_COMPONENTS = [
    "has_any_sanction",
    "sanction_reject_list",
    "sanction_financial",
    "sanction_other",
    "placement_mandate",
    "rank_order_zipper",
]

CODEBOOK_TEXT = """# Gender Quota Country-Year Panel Codebook

## Identifiers
- `iso3c`, `country_name`, `year`: inherited from `data/input/analysis_panel_clean_1990_2024.csv`.

## Quota classification
The main classification follows International IDEA/IPU/Stockholm University Global Database of Gender Quotas:
- `quota_strength_ordinal = 0`: No quota.
- `quota_strength_ordinal = 1`: Voluntary Political Party Quotas.
- `quota_strength_ordinal = 2`: Legislated / Legal Candidate Quotas.
- `quota_strength_ordinal = 3`: Reserved Seats Quotas.

If several rules coexist in a country-year, `quota_strength_ordinal` takes the maximum value and the type flags preserve coexistence:
- `quota_voluntary_party`
- `quota_legislated_candidate`
- `quota_reserved_seats`

## Enforcement variables
`quota_enforcement_score` is the sum of six separately retained components:
1. `has_any_sanction`
2. `sanction_reject_list`
3. `sanction_financial`
4. `sanction_other`
5. `placement_mandate`
6. `rank_order_zipper`

`quota_enforcement_index = quota_enforcement_score / 6`.
`quota_strength_augmented = quota_strength_ordinal + 0.50 * quota_enforcement_index`.
Use the augmented measure only as a robustness/intensity measure; the ordinal classification and the enforcement components should be retained in main models.

## Target stage and authority
- `target_stage_score = 0`: none.
- `target_stage_score = 1`: party candidate selection stage.
- `target_stage_score = 2`: candidate nomination / candidate list stage.
- `target_stage_score = 3`: elected seats / seat allocation stage.

- `mandating_authority_level = 0`: none.
- `mandating_authority_level = 1`: party statute or internal party rule.
- `mandating_authority_level = 2`: national/subnational ordinary law or electoral law.
- `mandating_authority_level = 3`: constitutional provision.

## State-capacity mechanism variables
- `control_capacity_index = normalized state capacity * (1 - normalized democracy)`.
- `inclusive_capacity_index = normalized state capacity * normalized democracy`.
- `state_capacity_fsi_reversed`: reverse min-max of Fragile States Index total score when FSI is downloaded.
- `seat_redistribution_cost_observed`: observed proxy based on majoritarian/single-member system, national scope, seat-result target stage, and constitutional amendment requirement.

## Manual coding rule
The public IDEA country pages provide standardized current classifications and legal/source text. Historical intervals, enforcement details, and constitutional-change timing should be entered in `data/manual/quota_events_manual.csv` after checking IDEA country pages plus national parliament, election commission, electoral law, constitutional text, or other authoritative country sources.
"""
