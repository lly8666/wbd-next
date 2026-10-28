# PLAN025 H314a — N0 exact-source preflight correction

At SOURCE 9091c80d Actions40627126513 stopped in the cheapest wiring-contract job before any product build. First fault: tests/test_delivery_ci.py asserted the old exact workflow environment string, rejecting the new explicitly tagged main one-scenario selector. Governance and maintenance failed on the same test; existing new Npcap delta helper tests passed in maintenance. No native result or performance qualification from this source.

This source updates the test to enforce BOTH existing explicit manual-mode behavior and a main-only [plan025-n0-240s] Normal-only 240s selector, without weakening Stop or deployment gates. Same product and measurement harness otherwise; new exact main SHA must be used by the whole Actions run. Preserves original FAIL as not a product failure.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked test correction for a new narrowly scoped N0 Actions selector; no product feature/config change."}
```
