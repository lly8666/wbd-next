# PLAN027 H514 — corrected oracle assembly passed; isolated necessary native followups

At H513 initial `SOURCE eacb4c2` workflow 41053250222 failed before any native runner (Python unmatched parenthesis), governance 41053250022 also FAILED. Fixed exactly one closing parenthesis at `80517bbc`; current main preflight [41053357119](https://github.com/lly8666/wbd-next/actions/runs/41053357119), governance [41053356929](https://github.com/lly8666/wbd-next/actions/runs/41053356929) and maintenance [41053360438](https://github.com/lly8666/wbd-next/actions/runs/41053360438) all PASS. H513 dispatched Game2 recheck Action41053266961 was pinned to old malformed eacb harness and failed before native execution; not a Game2 product failure and **not acceptable as retest**.

H514 uses same fully frozen original Windows+Linux product build `SOURCE 1644df34d241d487c5c5eb704a1a0a2e5f506f5e` from Action41041996161 (no rebuild). Five **separate Actions**, one true physical scenario per measurement controller: (1) Game2/off real 5%/75ms corrected damaged gate; (2) Game2 highest FEC 15%; (3) Game4 highest FEC 30% (both canceled previously, now rerun); (4) Fixed highest 50Mbps each 25ms/0%/60s after source-matched Fixed10mbps success; (5) A5 original Go→Rust same-VM sequential AB Normal/off 10Mbps/25ms loss0, after H499 Windows old-Go baseline failure. No new 5min run (C50 already complete).

This is not outer repair success. SOURCE1644 signed damage tiers have near-zero real R despite 1/5/10/30%, so following work must complete original-Go authenticated SACK cold flag and Rust-only ACK-only future spans, without blind PTO or synthetic repair. All five PLAN027 section0 items still PARTIAL. Stop, source PN, MTU, F/R/C and actual Linux/Windows driver measurements remain hard gates.

```feature-impact
{"kind":"none","reason":"H514 changes only one bounded source-locked Fixed50 scenario, one-shot Action fanout, cursor and devlog; no production semantics or feature entry changed."}
```
