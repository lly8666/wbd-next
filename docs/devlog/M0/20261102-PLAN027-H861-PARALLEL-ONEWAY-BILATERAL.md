# PLAN027 H861 | Two independent genuine cold Health scenarios, one original SOURCE

- H859/H860 source `377613dec8ea3b2fdd123079a580326c2ba52dfb` adds only numeric Go post-Health-dead stage timestamps to original Linux Go TLS, source immutable Go/Rust since then. Exact once-builder [Action 41378386073](https://github.com/lly8666/wbd-next/actions/runs/41378386073) currently active when these fixtures were prepared; three manifest SHA hashes must pass before measurement. H859 initial Action41378295483 failed PRE_BUILD on invalid checkout pin, H860 fixed the checkout; no old failed product evidence.
- Two strictly independent Actions on hosted Linux VMs, one scene per Action and stage logs sanitized by shared reporter:
  - **bilateral10**: original source old 20s active10Mbps each/25ms0%, 105s real both-way tc100% while source app/probes silent, 120s genuine restored10Mbps. Prior e928 same scenario first100/99.813%, 379 missing and source TUN27, ~1.25s gap; use newly captured `COLD_STAGE unix_ms` to locate SYN/Go/Rust phase, do not change acceptance.
  - **unilateral c2s-only105**: 2Mbps each active pre20/restore120, one actual c2s tc100% while reverse s2c healthy throughout blackout, same real Health90s, no source app/probe105, authentic asymmetric generation. Check actual tc client drops >0, source TUN drops, Go/Rust handoff, first/p99/missing and owned Stop; unilateral 2Mbps is lifecycle diagnosis, not 10Mbps performance qualification. If both sides cannot rejoin in 120s, report FAIL rather than fake green.
- Workflows copy only frozen manifest/three binaries from the same builder run using explicit run ID and actions:read. Each script takes exact product source, fixture source is its commit; no duplicate build, no main/product mutation during measurement. Separate runners are **not** sameVM CPU A/B. Main stage scope remains partial, Windows OFF still NOT_RUN.

```feature-impact
{"kind":"none","ids":[],"reason":"Add two source-locked independent real Health blackhole cases, with one-way loss fixture and stage evidence; no new product behavior, configuration or UI."}
```
