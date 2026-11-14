# PLAN029 H1786 | preflight false assertion corrected

- [H1785 Action 43550049582](https://github.com/lly8666/wbd-next/actions/runs/43550049582) **failed before build/native**, because H1783's stale test assumed **both** Windows and Linux source files read the same `WBD_PLAN029_DNS_CACHE_SCENE` Windows env variable. H1785 correctly changed Linux guest to explicit WSL argv, whose new regression passed. Governance maintenance reused the old assertion and failed. Do not claim any new real DNS/Stop outcome from this run.
- H1786 updates only the now-invalid historical test assertion: Windows fixture must still read its native environment, Linux fixture must read the exact `0|1` argument and never imply Windows env inheritance. End-to-end runner and 2.5s target-only physical DNS witness remain checked. One source-locked combined Action from the commit, not manual retries.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct obsolete test's WSL environment assumption without weakening product or network gates."}
```
