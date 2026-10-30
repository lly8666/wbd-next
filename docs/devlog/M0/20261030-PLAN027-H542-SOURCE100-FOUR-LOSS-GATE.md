# PLAN027 H542 — H541 build in flight, no duplicate source or four-scene dispatch

Original product SOURCE `10001c7eefb52387a5c71aa71129b80418273ac9` H541 new true Windows signed NPF/Wintun Go TLS + Linux Rust raw/TUN 0% Action [41085178791](https://github.com/lly8666/wbd-next/actions/runs/41085178791) in progress; Linux Rust/Windows Rust/Go build+unit gates already PASS (not native product PASS). H539 prior source2bc Action41084411982 has actual 1 stale test FAIL, retained. H540 [governance41084726559](https://github.com/lly8666/wbd-next/actions/runs/41084726559) PASS after cross-source ref cleanup.

H542 workflow `m0-plan027-h542-half-gap-loss-tiers.yml` listens only for Action41085178791 **workflow_dispatch attempt1** at exact source100, actual 0%/60s full two-OS completion SUCCESS. It checks Windows and Linux binary artifacts exist, parses exact original native Normal 0% first delivery both≥99.9% and owned Stop, checks Windows F/R/C no-loss chargedR≤0.1%F. **Only after this genuine gate** launch exactly four independent one-scenario Actions 1/5/15/30% (10Mbps each way, one-way250ms, 60s, same seed20261030, same packet mix; Windows and Linux both in each scene), all reuse frozen source100 binaries; parallel VMs are allowed, never same-VM overlapping loads. Artifact hash and run_id to be recorded on completion. A failed gate dispatches no scenes and must not be called PASS.

Latest user's target low R/F between0.4–0.6p and high0.25–0.6p capped10% remains OPEN pending real measurement; no seeded sweeps, no target ratio inferred from positive core tests. Game4FEC Windows cold startup actual failure Action41079630362 and Game2FEC Action41079626524 in flight remain separate necessary B work; prepared bounded early detached-M3 cold buffer change not in this source.

```feature-impact
{"kind":"none","ids":[],"reason":"Only source-gated workflow_run follow-up for four real independent rate scenarios after H541 existing true0%+Stop success, plus checkpoint; no data-plane or user-facing product change."}
```
