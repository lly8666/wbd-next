# PACK016 M3 → M0: fix exact-source GitHub API 403 in governance/scope-audit

Formal worker task: `R1-M3-RECORD-LINK-FEC-WORKPACK-016`.
Worker source `605f7de1507781f42d0bd6a002d9ee2d063b2764` Rust1.85.1 native [38999954180](https://github.com/lly8666/wbd-next/actions/runs/38999954180) PASS **106/106**.
This does **not** override a red governance result.

The M0-owned legacy `governance.yml` running worker checker fails on the GitHub REST compare endpoint, not on a detected forbidden path:
- [38999954233](https://github.com/lly8666/wbd-next/actions/runs/38999954233) `ROLE_SCOPE_FAILED: GitHub read failed HTTP 403: compare/83bd7203...605f7de1`.
- Earlier [38999528289](https://github.com/lly8666/wbd-next/actions/runs/38999528289) same legacy HTTP403 on compare ...1341d3.
The M0-owned `scope-audit.yml` has likewise failed with HTTP403 on varying normal content reads:
- [38999964044](https://github.com/lly8666/wbd-next/actions/runs/38999964044) `SCOPE_AUDIT_FAILED: GitHub read failed HTTP 403: contents/docs/devlog/M3/M0-REQUEST-PACK016-NATIVE-ISA-L.md`.
- [38999539066](https://github.com/lly8666/wbd-next/actions/runs/38999539066) HTTP403 on the M3 workpack devlog.
No successful exact-source central audit after `5aa8e662` is available. A prior [38998245589](https://github.com/lly8666/wbd-next/actions/runs/38998245589) passed earlier evidence source, but does not qualify the new SHA.

**M0 action requested:** make GitHub audit resilient to API 403 / rate limits without silently classifying unreadable content as PASS. Prefer a source/registry-pinned local git checkout and local ancestry diff for bytes/paths; where REST is unavoidable, identify permission vs rate limit and apply bounded retry. Keep branch/source/control drift fail-closed and retain exact SHA, file path, commit counts and run receipts. No M3 permission to edit shared `tools/*.py` or `.github/workflows/*`; no request to weaken path whitelist. Re-run exact-source and full S→H audit once fixed.

Separately, native ISA-L binding/build remains requested in `docs/devlog/M3/M0-REQUEST-PACK016-NATIVE-ISA-L.md`.
