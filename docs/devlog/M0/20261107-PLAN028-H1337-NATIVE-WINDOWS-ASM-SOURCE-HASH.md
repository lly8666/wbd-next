# PLAN028 H1337 — exact Windows original TLS assembly manifest updated

H1335 native Windows source b07d32c changed two Go files. All three original Go Windows Actions (42385505335 real signed Win↔WSL2, 42385505354 cold tests, 42385505336 real native WAL) failed **before network/build** because the authoritative assembly manifest's original result_blob hashes still pointed to old Go bytes. This is an actual CI SOURCE-lock FAIL and preserves its original conclusion; no real same-IP physical MTU notification or protected record observed.

Correct only the two exact `create` operation `result_blob` SHA values to the already verified Git blobs of the H1335 Go source and Go unit; preserve original Go donor and all 108 other operations. No product, ABI, configuration, VM limits, scenario, frontend or wire behavior changed. The real native single Normal mode must run on the new exact post-manifest SHA; do not start seven-mode repetitions. Keep H998 old same-socket shrink and H1317 genuine 5.18s historical FAIL.

```feature-impact
{"kind":"none","ids":[],"reason":"Only synchronize two original-Go overlay result hashes in authoritative source assembly manifest to existing H1335 changed files; no product or platform behavior changed."}
```
