from pathlib import Path

import pandas as pd

from gender_quota_panel.build_panel import build, expand_quota_events, make_parser
from gender_quota_panel.schema import EVENT_SCHEMA


def test_expand_quota_events_multiple_types():
    skeleton = pd.DataFrame({
        "iso3c": ["AAA", "AAA", "AAA"],
        "country_name": ["Aland", "Aland", "Aland"],
        "year": [2000, 2001, 2002],
    })
    events = pd.DataFrame([
        {
            "iso3c": "AAA", "country_name": "Aland", "start_year": 2000, "end_year": 2002,
            "quota_type": "voluntary_party", "target_stage": "party_candidate_selection",
            "mandating_authority": "party_statute", "has_any_sanction": 0,
            "sanction_reject_list": 0, "sanction_financial": 0, "sanction_other": 0,
            "placement_mandate": 0, "rank_order_zipper": 0, "requires_constitutional_amendment": 0,
        },
        {
            "iso3c": "AAA", "country_name": "Aland", "start_year": 2001, "end_year": 2002,
            "quota_type": "legislated_candidate", "target_stage": "candidate_nomination",
            "mandating_authority": "electoral_law", "has_any_sanction": 1,
            "sanction_reject_list": 1, "sanction_financial": 0, "sanction_other": 0,
            "placement_mandate": 1, "rank_order_zipper": 0, "requires_constitutional_amendment": 0,
        },
    ])
    out = expand_quota_events(skeleton, events, 2002)
    y2000 = out[out["year"] == 2000].iloc[0]
    y2001 = out[out["year"] == 2001].iloc[0]
    assert y2000["quota_strength_ordinal"] == 1
    assert y2001["quota_strength_ordinal"] == 2
    assert y2001["quota_voluntary_party"] == 1
    assert y2001["quota_legislated_candidate"] == 1
    assert y2001["quota_enforcement_score"] == 3


def test_offline_build_tiny_panel(tmp_path: Path):
    base = tmp_path / "base.csv"
    events = tmp_path / "events.csv"
    outdir = tmp_path / "data"
    pd.DataFrame({
        "iso3c": ["AAA", "AAA"],
        "country_name": ["Aland", "Aland"],
        "year": [2000, 2001],
        "state_capacity_clean_index_z": [0.1, 0.2],
        "ctrl_democracy_vdem": [0.5, 0.6],
        "ctrl_esys_family": ["PR", "PR"],
    }).to_csv(base, index=False)
    pd.DataFrame([{c: "" for c in EVENT_SCHEMA} | {
        "iso3c": "AAA", "country_name": "Aland", "start_year": 2001, "end_year": 2001,
        "quota_type": "reserved_seats", "target_stage": "seat_allocation", "mandating_authority": "constitution",
        "lower_house_scope": 1, "has_any_sanction": 1,
    }]).to_csv(events, index=False)
    args = make_parser().parse_args(["--base", str(base), "--quota-events", str(events), "--out", str(outdir), "--start", "2000", "--end", "2001", "--offline"])
    out_path = build(args)
    assert out_path.exists()
    df = pd.read_csv(out_path)
    assert len(df) == 2
    assert df.loc[df["year"] == 2001, "quota_strength_ordinal"].iloc[0] == 3
    assert "control_capacity_index" in df.columns
