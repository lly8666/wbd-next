# PLAN028 H1297 — capture Erin stalls without hot-worker observer effect

H1296 Action [42328445418](https://github.com/lly8666/wbd-next/actions/runs/42328445418), exact SOURCE `6bf586c4a98e63f294b3dc1acfab994f5997b8fa`, ran native ARM64 180s five-client pressure twice. Both scene attempts reported zero alerts, all five true Go TLS/Rust M4 rotations PASS, and all five server /32 TUN queues overflow0. H1295 earlier SOURCE `c635edc` still failed one genuine Erin Fixed6 uplink app gap in each pressure native/scalar/hetero 180s scene (6390/3310/2170ms). An opt-in diagnostic PASS is not a product fix.

**H1296 diagnosis was not time-aligned:** its `ns=loop_now().0` is per-process relative, whereas original 10ms app bins use Python CLOCK_MONOTONIC absolute. Its optional 500ms eprintln! ran INSIDE M4 RX and TX worker loops, potentially hiding a scheduler-sensitive bug.

H1297 keeps both existing real crypto/FEC/record/PN/packet paths unchanged. It adds a disabled-by-default independent Rust M4 stage observer sampling already existing atomic raw observed / filtered tuple / FEC source+parity+recovery / TUN delivered and M1 source staged / M4 copied / backpressure counts every 500ms. It tags exact original client port + generation and CLOCK_MONOTONIC ns, so app bins and all five clients can be causally compared without in-loop logging or per-packet instrumentation. The observer's owned handle is joined on exact Stop; no second TUN reader, no steady wire change, no user-facing extra config. Normal production does not spawn it.

A single native ARM64 pressure 180s workflow is source-pinned and asserts real server/client observer output with kernel clock alignment. Its original test gate is not weakened: if Erin gaps reappear the Action is FAIL, artifact retains the stage trace, and only the observed blocking stage should be fixed. No 1800s tests before all known short failures are clear.

```feature-impact
{"kind":"none","ids":[],"reason":"Opt-in diagnostic observer only, no packet-path behavior, configuration, user default, wire, owner authority or FEC change."}
```
