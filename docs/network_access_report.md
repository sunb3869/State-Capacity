# Network Access Diagnostic Report (Codex Container)

## Run metadata
- Date (UTC): 2026-05-28
- Environment: Codex container for `/workspace/State-Capacity`
- Purpose: verify access to official quota sources (IDEA and national legal portals)

## Access attempts and outcomes
| timestamp_utc | domain | url | result | error_type | proxy_tunnel_403 |
|---|---|---|---|---|---|
| 2026-05-28 | idea.int | https://www.idea.int/data-tools/data/gender-quotas/country-view/96/35 | failed | `ProxyError` / `Tunnel connection failed: 403 Forbidden` | yes |
| 2026-05-28 | legifrance.gouv.fr | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000394777 | failed | `ProxyError` / `Tunnel connection failed: 403 Forbidden` | yes |
| 2026-05-28 | legifrance.gouv.fr | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000000760568 | failed | `ProxyError` / `Tunnel connection failed: 403 Forbidden` | yes |

## Diagnostic conclusion
1. In this Codex run, official-source domains needed for historical verification are blocked by proxy tunnel failures (HTTP 403).
2. Because the manual coding protocol requires source-backed verification for `start_year`, `end_year`, enforcement details, `target_stage`, `mandating_authority`, and constitutional-amendment status, this run **must not** add unverifiable country records to `data/manual/quota_events_manual.csv`.
3. Therefore, this round focuses on workflow hardening, reproducibility, and an auditable offline source-intake process.

## Immediate rule for this repository
- If official sources are inaccessible in container runtime, set country workflow status to `blocked_in_codex_environment` in `data/manual/quota_country_todo.csv` and stop before adding new event rows.
