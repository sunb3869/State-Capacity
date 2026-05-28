from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from .schema import (
    CODEBOOK_TEXT,
    ENFORCEMENT_COMPONENTS,
    EVENT_SCHEMA,
    MANDATE_AUTHORITY_MAP,
    QUOTA_TYPE_MAP,
    TARGET_STAGE_MAP,
)

IDEA_COUNTRIES_URL = "https://www.idea.int/data-tools/data/gender-quotas-database/countries"
IDEA_BASE_URL = "https://www.idea.int"
WB_API = "https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&per_page=20000&date={start}:{end}"
FSI_EXCEL_URL = "https://fragilestatesindex.org/excel/"
WB_WOMEN_PARL_INDICATOR = "SG.GEN.PARL.ZS"
WGI_INDICATORS = {
    "GE.EST": "wgi_government_effectiveness_est",
    "VA.EST": "wgi_voice_accountability_est",
    "PV.EST": "wgi_political_stability_est",
    "RQ.EST": "wgi_regulatory_quality_est",
    "RL.EST": "wgi_rule_of_law_est",
    "CC.EST": "wgi_control_corruption_est",
}


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def clean_text(s: object) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def normalize_iso3(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.upper().replace({"NAN": np.nan, "": np.nan})


def bool01(x) -> int:
    if pd.isna(x):
        return 0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return int(x != 0)
    return int(str(x).strip().lower() in {"1", "yes", "y", "true", "t", "是", "是的"})


def minmax(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    lo, hi = x.min(skipna=True), x.max(skipna=True)
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(np.nan, index=x.index)
    return (x - lo) / (hi - lo)


def zscore(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    sd = x.std(skipna=True)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.nan, index=x.index)
    return (x - x.mean(skipna=True)) / sd


def request_text(url: str, cache_path: Path, sleep: float = 0.15) -> str:
    ensure_dir(cache_path.parent)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_text(encoding="utf-8", errors="ignore")
    r = requests.get(url, timeout=45, headers={"User-Agent": "gender-quota-panel-research/0.2"})
    r.raise_for_status()
    cache_path.write_text(r.text, encoding="utf-8")
    time.sleep(sleep)
    return r.text


def request_bytes(url: str, cache_path: Path, sleep: float = 0.15) -> bytes:
    ensure_dir(cache_path.parent)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_bytes()
    r = requests.get(url, timeout=75, headers={"User-Agent": "gender-quota-panel-research/0.2"})
    r.raise_for_status()
    cache_path.write_bytes(r.content)
    time.sleep(sleep)
    return r.content


def country_name_key(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.lower()
            .str.replace(r"[^a-z0-9]+", " ", regex=True)
            .str.replace(r"\b(the|republic|kingdom|state|states|of)\b", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip())


def load_skeleton(base_csv: Path, start: int, end: int) -> pd.DataFrame:
    df = pd.read_csv(base_csv, low_memory=False)
    required = {"iso3c", "country_name", "year"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Base CSV lacks required columns: {sorted(missing)}")
    df["iso3c"] = normalize_iso3(df["iso3c"])
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df[(df["year"] >= start) & (df["year"] <= end)].copy()
    df = df.drop_duplicates(["iso3c", "year"], keep="first")
    return df


# -----------------------------------------------------------------------------
# IDEA current data: optional scrape, used as a current summary and template seed
# -----------------------------------------------------------------------------

def scrape_idea_country_links(raw_dir: Path) -> pd.DataFrame:
    html = request_text(IDEA_COUNTRIES_URL, raw_dir / "idea_countries.html")
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = clean_text(a.get_text(" "))
        if "gender-quotas-database/country?country=" in href and text:
            m = re.search(r"country=(\d+)", href)
            if m:
                records.append({
                    "idea_country_id": int(m.group(1)),
                    "country_name_idea": text,
                    "idea_country_url": urljoin(IDEA_BASE_URL, href),
                })
    links = pd.DataFrame(records).drop_duplicates("idea_country_id")
    return links.sort_values(["country_name_idea", "idea_country_id"]).reset_index(drop=True)


def parse_idea_country_page(country_name: str, country_id: int, url: str, raw_dir: Path) -> dict:
    html = request_text(url, raw_dir / "idea_country_pages" / f"{country_id}.html")
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    text_clean = clean_text(text)

    def contains(pattern: str) -> bool:
        return re.search(pattern, text_clean, flags=re.I) is not None

    no_quota = contains(r"No legislated or voluntary party quotas")
    has_reserved = contains(r"Reserved\s+Seats") or contains(r"reserved\s+seats")
    has_leg_candidate = contains(r"Legislated\s+Candidate\s+Quotas") or contains(r"Legal\s+candidate\s+quotas")
    has_voluntary = contains(r"Voluntary\s+Political\s+Party\s+Quotas") or contains(r"Voluntary quotas adopted by political parties")
    legislated_lower = contains(r"Legislated quotas for the Single\s*/\s*Lower House") or contains(r"For the Single\s*/\s*Lower house\?\s*Yes")
    legislated_upper = contains(r"Legislated quotas for the Upper House") or contains(r"For the Upper house\?\s*Yes")
    legislated_subnat = contains(r"Legislated quotas at the Sub-national level") or contains(r"For the Sub-national level\?\s*Yes")

    if no_quota:
        type_guess, strength = "no_quota", 0
    elif has_reserved:
        type_guess, strength = "reserved_seats", 3
    elif has_leg_candidate or legislated_lower or legislated_upper:
        type_guess, strength = "legislated_candidate", 2
    elif has_voluntary:
        type_guess, strength = "voluntary_party", 1
    else:
        type_guess, strength = "needs_review", np.nan

    pct_match = re.search(r"Percentage of women\s+(\d+(?:\.\d+)?)%", text_clean)
    seats_match = re.search(r"Total seats\s+(\d+)", text_clean)
    women_match = re.search(r"Total women\s+(\d+)", text_clean)
    election_match = re.search(r"Election year\s+(\d{4})", text_clean)
    years = sorted(set(int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text_clean)))

    return {
        "idea_country_id": country_id,
        "country_name_idea": country_name,
        "idea_country_url": url,
        "idea_current_type_guess": type_guess,
        "idea_current_strength_guess": strength,
        "idea_has_reserved_text": int(has_reserved),
        "idea_has_legislated_candidate_text": int(has_leg_candidate or legislated_lower or legislated_upper or legislated_subnat),
        "idea_has_voluntary_text": int(has_voluntary),
        "idea_legislated_lower": int(legislated_lower),
        "idea_legislated_upper": int(legislated_upper),
        "idea_legislated_subnational": int(legislated_subnat),
        "idea_no_quota_text": int(no_quota),
        "idea_total_seats_current": int(seats_match.group(1)) if seats_match else np.nan,
        "idea_total_women_current": int(women_match.group(1)) if women_match else np.nan,
        "idea_women_pct_current": float(pct_match.group(1)) if pct_match else np.nan,
        "idea_election_year_current": int(election_match.group(1)) if election_match else np.nan,
        "idea_year_candidates_in_text": ";".join(map(str, years)),
        "idea_page_text_excerpt": text_clean[:2500],
    }


def scrape_idea_current(raw_dir: Path, derived_dir: Path, strict: bool = False) -> pd.DataFrame:
    try:
        links = scrape_idea_country_links(raw_dir)
    except Exception as e:
        if strict:
            raise
        print(f"WARNING: could not scrape IDEA country links: {e}", file=sys.stderr)
        return pd.DataFrame()
    records = []
    for _, row in links.iterrows():
        try:
            records.append(parse_idea_country_page(row.country_name_idea, int(row.idea_country_id), row.idea_country_url, raw_dir))
        except Exception as e:
            if strict:
                raise
            records.append({
                "idea_country_id": row.idea_country_id,
                "country_name_idea": row.country_name_idea,
                "idea_country_url": row.idea_country_url,
                "idea_parse_error": str(e),
            })
    out = pd.DataFrame(records)
    ensure_dir(derived_dir)
    out.to_csv(derived_dir / "idea_current_country_summary.csv", index=False)
    return out


def blank_event_template(countries: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in countries[["iso3c", "country_name"]].drop_duplicates().iterrows():
        rows.append({c: "" for c in EVENT_SCHEMA} | {
            "iso3c": r["iso3c"],
            "country_name": r["country_name"],
            "quota_type": "",
            "confidence": "not_coded",
            "notes": "Fill only when a verified quota interval exists; no-quota years are created automatically.",
        })
    return pd.DataFrame(rows, columns=EVENT_SCHEMA)


def make_events_template(skeleton: pd.DataFrame, idea_current: pd.DataFrame, manual_dir: Path) -> pd.DataFrame:
    ensure_dir(manual_dir)
    countries = skeleton[["iso3c", "country_name"]].drop_duplicates().copy()
    if idea_current is None or idea_current.empty or "idea_current_strength_guess" not in idea_current.columns:
        template = blank_event_template(countries)
        template.to_csv(manual_dir / "quota_events_template.csv", index=False)
        if not (manual_dir / "quota_events_manual.csv").exists():
            template.head(0).to_csv(manual_dir / "quota_events_manual.csv", index=False)
        return template

    countries["name_key"] = country_name_key(countries["country_name"])
    idea = idea_current.copy()
    idea["name_key"] = country_name_key(idea["country_name_idea"])
    merged = countries.merge(idea, on="name_key", how="left")
    rows = []
    for _, r in merged.iterrows():
        strength_val = pd.to_numeric(r.get("idea_current_strength_guess"), errors="coerce")
        if pd.isna(strength_val) or strength_val <= 0:
            continue
        strength = int(strength_val)
        qtype = {1: "voluntary_party", 2: "legislated_candidate", 3: "reserved_seats"}.get(strength, "needs_review")
        target_stage = "seat_allocation" if strength == 3 else ("candidate_nomination" if strength == 2 else "party_candidate_selection")
        rows.append({
            "iso3c": r["iso3c"],
            "country_name": r["country_name"],
            "start_year": "",
            "end_year": "",
            "quota_type": qtype,
            "quota_strength_base": strength,
            "target_stage": target_stage,
            "target_stage_score": {"party_candidate_selection": 1, "candidate_nomination": 2, "seat_allocation": 3}[target_stage],
            "mandating_authority": "constitution_or_law" if strength in (2, 3) else "party_statute",
            "mandating_authority_level": 2 if strength in (2, 3) else 1,
            "level_scope": "single_lower_house" if r.get("idea_legislated_lower", 0) == 1 else "needs_review",
            "lower_house_scope": r.get("idea_legislated_lower", 0),
            "upper_house_scope": r.get("idea_legislated_upper", 0),
            "subnational_scope": r.get("idea_legislated_subnational", 0),
            "quota_target_percent": "",
            "reserved_seats_number": "",
            "has_any_sanction": "",
            "sanction_reject_list": "",
            "sanction_financial": "",
            "sanction_other": "",
            "placement_mandate": "",
            "rank_order_zipper": "",
            "requires_constitutional_amendment": "",
            "legal_basis": "",
            "source_url": r.get("idea_country_url", ""),
            "source_quote": "",
            "source_type": "IDEA current summary; verify with law/parliament/election source",
            "coder": "",
            "confidence": "low_until_verified",
            "notes": f"IDEA current type guess={qtype}; years mentioned={r.get('idea_year_candidates_in_text','')}",
        })
    template = pd.DataFrame(rows, columns=EVENT_SCHEMA)
    template.to_csv(manual_dir / "quota_events_template.csv", index=False)
    manual_path = manual_dir / "quota_events_manual.csv"
    if not manual_path.exists():
        template.head(0).to_csv(manual_path, index=False)
    return template


# -----------------------------------------------------------------------------
# Manual events to country-year panel
# -----------------------------------------------------------------------------

def normalize_event_codes(events: pd.DataFrame, panel_end: int) -> pd.DataFrame:
    events = events.copy()
    for col in EVENT_SCHEMA:
        if col not in events.columns:
            events[col] = np.nan
    events["iso3c"] = normalize_iso3(events["iso3c"])
    events["country_name"] = events["country_name"].map(clean_text)
    events["start_year"] = pd.to_numeric(events["start_year"], errors="coerce")
    events["end_year"] = pd.to_numeric(events["end_year"], errors="coerce").fillna(panel_end)
    events = events.dropna(subset=["iso3c", "start_year"]).copy()
    if events.empty:
        return events
    events["start_year"] = events["start_year"].astype(int)
    events["end_year"] = events["end_year"].astype(int)

    def q_strength(row: pd.Series) -> float:
        raw = str(row.get("quota_type", "")).strip().lower()
        if raw in QUOTA_TYPE_MAP:
            return float(QUOTA_TYPE_MAP[raw])
        return pd.to_numeric(row.get("quota_strength_base", np.nan), errors="coerce")

    events["quota_strength_base"] = events.apply(q_strength, axis=1).astype(float)
    events["target_stage_score"] = events.apply(
        lambda r: TARGET_STAGE_MAP.get(str(r.get("target_stage", "")).strip().lower(), pd.to_numeric(r.get("target_stage_score"), errors="coerce")),
        axis=1,
    ).astype(float)
    events["mandating_authority_level"] = events.apply(
        lambda r: MANDATE_AUTHORITY_MAP.get(str(r.get("mandating_authority", "")).strip().lower(), pd.to_numeric(r.get("mandating_authority_level"), errors="coerce")),
        axis=1,
    ).astype(float)
    bool_cols = [
        "lower_house_scope", "upper_house_scope", "subnational_scope",
        "has_any_sanction", "sanction_reject_list", "sanction_financial", "sanction_other",
        "placement_mandate", "rank_order_zipper", "requires_constitutional_amendment",
    ]
    for c in bool_cols:
        events[c] = events[c].map(bool01)
    events["quota_target_percent"] = pd.to_numeric(events["quota_target_percent"], errors="coerce")
    events["reserved_seats_number"] = pd.to_numeric(events["reserved_seats_number"], errors="coerce")
    return events


def empty_quota_panel(skeleton: pd.DataFrame) -> pd.DataFrame:
    out = skeleton[["iso3c", "country_name", "year"]].copy()
    zero_cols = [
        "has_quota", "quota_strength_ordinal", "quota_voluntary_party", "quota_legislated_candidate",
        "quota_reserved_seats", "target_stage_score", "mandating_authority_level", "lower_house_scope",
        "upper_house_scope", "subnational_scope", "has_any_sanction", "sanction_reject_list",
        "sanction_financial", "sanction_other", "placement_mandate", "rank_order_zipper",
        "requires_constitutional_amendment", "quota_enforcement_score", "quota_enforcement_index",
        "quota_strength_augmented", "quota_adopted_this_year_new",
        "quota_target_percent", "reserved_seats_number",
    ]
    for c in zero_cols:
        out[c] = 0
    out["source_url"] = ""
    out["legal_basis"] = ""
    out["notes"] = ""
    return out


def expand_quota_events(skeleton: pd.DataFrame, events: pd.DataFrame, panel_end: int) -> pd.DataFrame:
    events = normalize_event_codes(events, panel_end)
    if events.empty:
        return empty_quota_panel(skeleton)

    expanded_rows: list[dict] = []
    for _, r in events.iterrows():
        for y in range(int(r.start_year), int(r.end_year) + 1):
            row = r.to_dict()
            row["year"] = y
            expanded_rows.append(row)
    if not expanded_rows:
        return empty_quota_panel(skeleton)

    exp = pd.DataFrame(expanded_rows)
    exp["quota_voluntary_party"] = (exp["quota_strength_base"] == 1).astype(int)
    exp["quota_legislated_candidate"] = (exp["quota_strength_base"] == 2).astype(int)
    exp["quota_reserved_seats"] = (exp["quota_strength_base"] == 3).astype(int)
    exp["quota_enforcement_score_event"] = exp[ENFORCEMENT_COMPONENTS].sum(axis=1)
    exp["quota_enforcement_index_event"] = exp["quota_enforcement_score_event"] / len(ENFORCEMENT_COMPONENTS)

    join_text = lambda x: " | ".join(sorted(set(clean_text(v) for v in x if clean_text(v))))[:1200]
    agg_dict = {
        "quota_strength_base": "max",
        "quota_voluntary_party": "max",
        "quota_legislated_candidate": "max",
        "quota_reserved_seats": "max",
        "target_stage_score": "max",
        "mandating_authority_level": "max",
        "lower_house_scope": "max",
        "upper_house_scope": "max",
        "subnational_scope": "max",
        "quota_target_percent": "max",
        "reserved_seats_number": "max",
        "has_any_sanction": "max",
        "sanction_reject_list": "max",
        "sanction_financial": "max",
        "sanction_other": "max",
        "placement_mandate": "max",
        "rank_order_zipper": "max",
        "requires_constitutional_amendment": "max",
        "quota_enforcement_score_event": "max",
        "quota_enforcement_index_event": "max",
        "source_url": join_text,
        "legal_basis": join_text,
        "notes": join_text,
    }
    q = exp.groupby(["iso3c", "year"], as_index=False).agg(agg_dict)
    q = q.rename(columns={
        "quota_strength_base": "quota_strength_ordinal",
        "quota_enforcement_score_event": "quota_enforcement_score",
        "quota_enforcement_index_event": "quota_enforcement_index",
    })
    q["has_quota"] = (q["quota_strength_ordinal"].fillna(0) > 0).astype(int)
    q["quota_strength_augmented"] = q["quota_strength_ordinal"] + 0.50 * q["quota_enforcement_index"].fillna(0)
    q.loc[q["has_quota"] == 0, "quota_strength_augmented"] = 0

    out = skeleton[["iso3c", "country_name", "year"]].merge(q, on=["iso3c", "year"], how="left")
    out = out.fillna({"source_url": "", "legal_basis": "", "notes": ""})
    for c in empty_quota_panel(skeleton).columns:
        if c not in out.columns:
            out[c] = 0 if c not in {"source_url", "legal_basis", "notes"} else ""
    numeric_zero_cols = [c for c in out.columns if c not in {"iso3c", "country_name", "source_url", "legal_basis", "notes"}]
    for c in numeric_zero_cols:
        if c != "year":
            out[c] = out[c].fillna(0)
    out = out.sort_values(["iso3c", "year"]).copy()
    out["quota_adopted_this_year_new"] = out.groupby("iso3c")["has_quota"].transform(lambda s: ((s == 1) & (s.shift(fill_value=0) == 0)).astype(int))
    return out


# -----------------------------------------------------------------------------
# Optional external data
# -----------------------------------------------------------------------------

def download_world_bank_indicator(indicator: str, value_name: str, start: int, end: int, raw_dir: Path) -> pd.DataFrame:
    url = WB_API.format(indicator=indicator, start=start, end=end)
    text = request_text(url, raw_dir / "worldbank" / f"{indicator}_{start}_{end}.json", sleep=0.05)
    js = json.loads(text)
    if not isinstance(js, list) or len(js) < 2:
        raise ValueError(f"Unexpected World Bank API response for {indicator}: {str(js)[:200]}")
    rows = []
    for item in js[1]:
        if item.get("countryiso3code"):
            rows.append({
                "iso3c": item.get("countryiso3code"),
                "country_name_wb": item.get("country", {}).get("value"),
                "year": int(item.get("date")),
                value_name: item.get("value"),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["iso3c", "year", value_name])
    df["iso3c"] = normalize_iso3(df["iso3c"])
    df[value_name] = pd.to_numeric(df[value_name], errors="coerce")
    return df[["iso3c", "year", value_name, "country_name_wb"]]


def download_wgi(start: int, end: int, raw_dir: Path) -> pd.DataFrame:
    pieces = []
    for ind, name in WGI_INDICATORS.items():
        df = download_world_bank_indicator(ind, name, start, end, raw_dir)
        pieces.append(df.drop(columns=["country_name_wb"], errors="ignore"))
    out = pieces[0]
    for p in pieces[1:]:
        out = out.merge(p, on=["iso3c", "year"], how="outer")
    return out


def download_fsi(raw_dir: Path, strict: bool = False) -> pd.DataFrame:
    try:
        html = request_text(FSI_EXCEL_URL, raw_dir / "fsi" / "fsi_excel_page.html")
    except Exception as e:
        if strict:
            raise
        print(f"WARNING: Could not access FSI excel page: {e}", file=sys.stderr)
        return pd.DataFrame(columns=["country_name_fsi", "year", "fsi_total_score"])
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        text = clean_text(a.get_text(" "))
        m = re.fullmatch(r"(20\d{2})", text)
        if m:
            links.append((int(m.group(1)), urljoin(FSI_EXCEL_URL, a["href"])))
    frames = []
    for year, url in sorted(set(links)):
        try:
            ext = ".xlsx" if ".xlsx" in url.lower() else ".xls"
            content = request_bytes(url, raw_dir / "fsi" / f"fsi_{year}{ext}")
            df = pd.read_excel(io.BytesIO(content))
            df.columns = [clean_text(c) for c in df.columns]
            country_col = next((c for c in df.columns if c.lower() in {"country", "country name"} or "country" in c.lower()), None)
            total_col = next((c for c in df.columns if c.lower() in {"total", "total score", "fsi score", "score"}), None)
            if country_col is None:
                continue
            if total_col is None:
                num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                total_col = num_cols[-1] if num_cols else None
            if total_col is None:
                continue
            tmp = df[[country_col, total_col]].copy().rename(columns={country_col: "country_name_fsi", total_col: "fsi_total_score"})
            tmp["year"] = year
            tmp["fsi_total_score"] = pd.to_numeric(tmp["fsi_total_score"], errors="coerce")
            frames.append(tmp.dropna(subset=["country_name_fsi", "fsi_total_score"]))
        except Exception as e:
            if strict:
                raise
            print(f"WARNING: FSI parse failed for {year}: {e}", file=sys.stderr)
    if not frames:
        return pd.DataFrame(columns=["country_name_fsi", "year", "fsi_total_score"])
    return pd.concat(frames, ignore_index=True)


def load_vdem_optional(vdem_path: Optional[Path]) -> pd.DataFrame:
    if not vdem_path or not vdem_path.exists():
        return pd.DataFrame(columns=["iso3c", "year", "vdem_polyarchy", "vdem_liberal_democracy"])
    if vdem_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(vdem_path) as zf:
            csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(csv_name) as f:
                df = pd.read_csv(f, low_memory=False)
    else:
        df = pd.read_csv(vdem_path, low_memory=False)
    iso_col = "country_text_id" if "country_text_id" in df.columns else ("iso3c" if "iso3c" in df.columns else None)
    if iso_col is None or "year" not in df.columns:
        raise ValueError("V-Dem file needs country_text_id or iso3c plus year columns")
    keep_map = {iso_col: "iso3c", "year": "year"}
    if "v2x_polyarchy" in df.columns:
        keep_map["v2x_polyarchy"] = "vdem_polyarchy"
    if "v2x_libdem" in df.columns:
        keep_map["v2x_libdem"] = "vdem_liberal_democracy"
    out = df[list(keep_map.keys())].rename(columns=keep_map)
    out["iso3c"] = normalize_iso3(out["iso3c"])
    return out


def merge_fsi_to_iso(panel: pd.DataFrame, fsi: pd.DataFrame) -> pd.DataFrame:
    if fsi.empty:
        panel["fsi_total_score"] = np.nan
        return panel
    names = panel[["iso3c", "country_name"]].drop_duplicates().copy()
    names["name_key"] = country_name_key(names["country_name"])
    fsi = fsi.copy()
    fsi["name_key"] = country_name_key(fsi["country_name_fsi"])
    fsi2 = fsi.merge(names[["iso3c", "name_key"]], on="name_key", how="left")
    return panel.merge(fsi2[["iso3c", "year", "fsi_total_score"]], on=["iso3c", "year"], how="left")


# -----------------------------------------------------------------------------
# Mechanism variables
# -----------------------------------------------------------------------------

def first_available(out: pd.DataFrame, candidates: list[str]) -> tuple[pd.Series, str]:
    for c in candidates:
        if c in out.columns and out[c].notna().any():
            return pd.to_numeric(out[c], errors="coerce"), c
    return pd.Series(np.nan, index=out.index), "missing"


def compute_capacity_and_cost(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    cap, cap_src = first_available(out, [
        "wgi_government_effectiveness_est",
        "state_capacity_clean_index_z",
        "state_capacity_core_index_z",
        "state_capacity_broad_index_z",
    ])
    dem, dem_src = first_available(out, [
        "vdem_polyarchy",
        "ctrl_democracy_vdem",
        "wgi_voice_accountability_est",
    ])
    out["capacity_base_raw"] = cap
    out["capacity_base_source"] = cap_src
    out["democracy_base_raw"] = dem
    out["democracy_base_source"] = dem_src
    out["capacity_base_norm"] = minmax(out["capacity_base_raw"])
    out["democracy_base_norm"] = minmax(out["democracy_base_raw"])
    out["control_capacity_index"] = out["capacity_base_norm"] * (1 - out["democracy_base_norm"])
    out["inclusive_capacity_index"] = out["capacity_base_norm"] * out["democracy_base_norm"]
    out["control_capacity_index_z"] = zscore(out["control_capacity_index"])
    out["inclusive_capacity_index_z"] = zscore(out["inclusive_capacity_index"])

    if "fsi_total_score" in out.columns and out["fsi_total_score"].notna().any():
        out["state_capacity_fsi_reversed"] = 1 - minmax(out["fsi_total_score"])
        out["state_capacity_fsi_reversed_z"] = zscore(out["state_capacity_fsi_reversed"])
    else:
        out["state_capacity_fsi_reversed"] = np.nan
        out["state_capacity_fsi_reversed_z"] = np.nan

    esys = out.get("ctrl_esys_family", pd.Series("", index=out.index)).astype(str).str.upper()
    out["single_member_or_majoritarian_system"] = esys.str.contains("FPTP|TRS|PBV|BV|MAJORITARIAN", regex=True).astype(int)
    out["national_scope_quota"] = ((out.get("lower_house_scope", 0).fillna(0) == 1) | (out.get("upper_house_scope", 0).fillna(0) == 1)).astype(int)
    out["seat_result_stage_quota"] = (out.get("target_stage_score", 0).fillna(0) >= 3).astype(int)
    for c in ["requires_constitutional_amendment"]:
        if c not in out.columns:
            out[c] = 0
    cost_cols = [
        "single_member_or_majoritarian_system",
        "national_scope_quota",
        "seat_result_stage_quota",
        "requires_constitutional_amendment",
    ]
    out["seat_redistribution_cost_observed"] = out[cost_cols].mean(axis=1)
    out["seat_redistribution_cost_observed_z"] = zscore(out["seat_redistribution_cost_observed"])

    lag_cols = [
        "control_capacity_index", "inclusive_capacity_index", "seat_redistribution_cost_observed",
        "quota_strength_ordinal", "women_lower_house_pct_wb_ipu",
    ]
    out = out.sort_values(["iso3c", "year"]).copy()
    for c in lag_cols:
        if c in out.columns:
            out[f"L1_{c}"] = out.groupby("iso3c")[c].shift(1)
    return out


# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

def write_codebook(derived_dir: Path) -> None:
    (derived_dir / "codebook_quota_panel.md").write_text(CODEBOOK_TEXT, encoding="utf-8")


def validate_outputs(panel: pd.DataFrame, skeleton: pd.DataFrame, derived_dir: Path) -> None:
    problems = []
    if panel.duplicated(["iso3c", "year"]).any():
        problems.append("Duplicate iso3c-year keys in output")
    if len(panel) != len(skeleton):
        problems.append(f"Output row count {len(panel)} != skeleton row count {len(skeleton)}")
    if "quota_strength_ordinal" in panel.columns:
        bad_strength = panel[~panel["quota_strength_ordinal"].fillna(0).isin([0, 1, 2, 3])]
        if len(bad_strength):
            problems.append(f"Invalid quota_strength_ordinal rows: {len(bad_strength)}")
        summary = (panel.groupby("year")["quota_strength_ordinal"].value_counts(dropna=False).rename("n").reset_index())
        summary.to_csv(derived_dir / "diagnostics_quota_strength_by_year.csv", index=False)
    if problems:
        (derived_dir / "VALIDATION_WARNINGS.txt").write_text("\n".join(problems), encoding="utf-8")
        print("VALIDATION WARNINGS:\n" + "\n".join(problems), file=sys.stderr)


def read_or_init_events(manual_path: Path) -> pd.DataFrame:
    if not manual_path.exists():
        ensure_dir(manual_path.parent)
        pd.DataFrame(columns=EVENT_SCHEMA).to_csv(manual_path, index=False)
    try:
        return pd.read_csv(manual_path, low_memory=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=EVENT_SCHEMA)


def build(args: argparse.Namespace) -> Path:
    raw_dir = args.out / "raw"
    manual_dir = args.out / "manual"
    derived_dir = args.out / "derived"
    for d in [raw_dir, manual_dir, derived_dir]:
        ensure_dir(d)

    skeleton = load_skeleton(args.base, args.start, args.end)
    skeleton.to_csv(derived_dir / "country_year_skeleton.csv", index=False)
    print(f"Loaded skeleton: {len(skeleton)} rows, {skeleton.iso3c.nunique()} countries, years {skeleton.year.min()}-{skeleton.year.max()}")

    idea_current = pd.DataFrame()
    if args.fetch_idea and not args.offline:
        idea_current = scrape_idea_current(raw_dir, derived_dir, strict=args.strict)
    else:
        cached = derived_dir / "idea_current_country_summary.csv"
        if cached.exists():
            idea_current = pd.read_csv(cached, low_memory=False)

    make_events_template(skeleton, idea_current, manual_dir)
    manual_events_path = args.quota_events or (manual_dir / "quota_events_manual.csv")
    events = read_or_init_events(manual_events_path)
    quota_panel = expand_quota_events(skeleton, events, args.end)
    quota_panel.to_csv(derived_dir / "quota_panel_from_manual_events.csv", index=False)

    # Merge new quota data with the full original base panel, preserving all existing controls.
    panel = skeleton.merge(
        quota_panel.drop(columns=["country_name"], errors="ignore"),
        on=["iso3c", "year"],
        how="left",
    )

    if args.download_worldbank and not args.offline:
        women = download_world_bank_indicator(WB_WOMEN_PARL_INDICATOR, "women_lower_house_pct_wb_ipu", args.start, args.end, raw_dir)
        women.to_csv(derived_dir / "women_parliament_worldbank_ipu.csv", index=False)
        panel = panel.merge(women.drop(columns=["country_name_wb"], errors="ignore"), on=["iso3c", "year"], how="left")
    elif "ctrl_women_lower_house_lag1" in panel.columns and "women_lower_house_pct_wb_ipu" not in panel.columns:
        # Keep an explicit placeholder to avoid downstream KeyErrors.
        panel["women_lower_house_pct_wb_ipu"] = np.nan

    if args.download_wgi and not args.offline:
        wgi = download_wgi(args.start, args.end, raw_dir)
        wgi.to_csv(derived_dir / "wgi_selected_indicators.csv", index=False)
        panel = panel.merge(wgi, on=["iso3c", "year"], how="left")

    if args.download_fsi and not args.offline:
        fsi = download_fsi(raw_dir, strict=args.strict)
        fsi.to_csv(derived_dir / "fragile_states_index_long_rawparsed.csv", index=False)
        panel = merge_fsi_to_iso(panel, fsi)
    else:
        panel["fsi_total_score"] = np.nan

    vdem = load_vdem_optional(args.vdem)
    if not vdem.empty:
        vdem.to_csv(derived_dir / "vdem_selected.csv", index=False)
        panel = panel.merge(vdem, on=["iso3c", "year"], how="left")

    panel = compute_capacity_and_cost(panel)
    if "quota_strength_3cat" in panel.columns:
        panel["quota_strength_3cat_original"] = panel["quota_strength_3cat"]

    out_path = derived_dir / f"master_gender_quota_panel_{args.start}_{args.end}.csv"
    panel.to_csv(out_path, index=False)
    # Stable alias for scripts.
    panel.to_csv(derived_dir / "master_gender_quota_panel_1990_2024.csv", index=False)
    write_codebook(derived_dir)
    validate_outputs(panel, skeleton, derived_dir)
    print(f"DONE. Main output: {out_path}")
    print(f"Manual event file: {manual_events_path}")
    return out_path


def make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Build a gender quota country-year panel aligned to an existing base panel.")
    ap.add_argument("--base", required=True, type=Path, help="Existing base panel CSV with iso3c, country_name, year.")
    ap.add_argument("--start", type=int, default=1990)
    ap.add_argument("--end", type=int, default=2024)
    ap.add_argument("--out", type=Path, default=Path("data"))
    ap.add_argument("--quota-events", type=Path, default=None, help="Manual quota events CSV; defaults to data/manual/quota_events_manual.csv.")
    ap.add_argument("--vdem", type=Path, default=None, help="Optional local V-Dem country-year CSV or ZIP.")
    ap.add_argument("--offline", action="store_true", help="Do not access the internet; use local/manual files only.")
    ap.add_argument("--fetch-idea", action="store_true", help="Fetch current country summaries from IDEA/IPU/Stockholm database.")
    ap.add_argument("--download-worldbank", action="store_true", help="Download women in parliament indicator from World Bank/IPU series.")
    ap.add_argument("--download-wgi", action="store_true", help="Download selected WGI indicators from World Bank API.")
    ap.add_argument("--download-fsi", action="store_true", help="Download and parse Fragile States Index Excel files.")
    ap.add_argument("--strict", action="store_true", help="Fail on external scrape/download errors instead of warning.")
    return ap


def main(argv: Optional[list[str]] = None) -> None:
    args = make_parser().parse_args(argv)
    build(args)


if __name__ == "__main__":
    main()
