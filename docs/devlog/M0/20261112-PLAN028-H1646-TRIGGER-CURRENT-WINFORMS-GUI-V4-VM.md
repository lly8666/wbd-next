# PLAN028 H1646 | Restore actual GUI VM trigger after H1645 source-only fix

Current main `23b37087b6249d818bee63fc405b036fb812b69d`: completed real targeted cold Go V4 AES `fec-mode=legacy`+parity0 normalization to the existing protected Off carrier (no cipher/FEC downgrade) and effective config readback, manifest exact blobs plus source-lock; H1645 governance [Action43154543644](https://github.com/lly8666/wbd-next/actions/runs/43154543644) **SUCCESS**, prior H1644 evidence missing top-level SOURCE repaired. The original Windows GUI Action43153401230 FAIL retained, with 251 actual field/7-mode checks PASS only; failed on selected AES128 legacy policy. Original source8a previous seven signed native results retain old source scope, current Go cold change not yet requalified for signed networking.

The GUI workflow `.github/workflows/m0-plan028-h1638-windows-gui-all-controls-vm.yml` previously only listened for its own file's push path; H1645 manifest change did NOT trigger it. This H1646 edit makes it also listen for the formal `r0/go_overlay/assembly/manifest-plan020-m0.json` and permits explicit `workflow_dispatch`. Only ONE Windows2025 VM compiled real current Go + WinForms 53-field/7-mode/3-cipher + button suite should run from this trigger, no old product binary reuse for new cold Go. Keep fake session button test and true signed Wintun/OS qualifications separate. No protocol/Go/Rust defaults changed by this trigger.

Pending true result from Action workflow itself; do not assume until original VM report/checks and screenshots. Source8a Linux five-client original 180s strict offline rejudge Action43152631016 SUCCESS, raw native failed Action43148997176 preserved. Missing independent Win A/B/C L3, user-skipped nearMTU/dual Wintun unchanged. No 029/030.

```feature-impact
{"kind":"none","ids":[],"reason":"GUI VM workflow dispatch/manifest trigger scope only; compile-test current formal GUI source without changes to product or default."}
```
