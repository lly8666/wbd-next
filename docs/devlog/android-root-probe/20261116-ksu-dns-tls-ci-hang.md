# Same-source KSU DNS/TLS real network PASS but ACTION FAIL due EXIT wait (2026-11-16)

Real Action [43839583300](https://github.com/lly8666/wbd-next/actions/runs/43839583300) ran SOURCE `e1d73f4046b5f8c36958159a9c339d1403eaf7e3`. **All functional gates themselves PASS**: `appflow/summary.json APP_UID_TUN_ROUNDTRIP_PASS`, `mainstream/summary.json MAINSTREAM_DNS_TLS_PASS` errors=[], real Android Network100 `getAllByName("example.com")` returned IPv4/IPv6 in 11ms, actual JSSE TLS1.3 cipher TLS_AES_256_GCM_SHA384 with cert/hostname verification and host nonce verified, and `appflow-crash/summary.json SIGKILL_WATCHDOG_CLEANUP_PASS`. The complete `ksu/summary.json` was written by 09:29 UTC. **However overall Action is FAIL**, because the old shell EXIT trap waited unboundedly for an emulator process that did not exit, until the outer 780s timeout around 09:40 UTC. Do NOT reclassify the failed Action as SUCCESS.

Evidence: artifact 14212689127 ZIP SHA256 `49cc4e33ca7ed41ea351da43a2840097c17b71e5f7f7031d407bf5abfbd91555`; 115 actual files, independently downloaded and checked. This commit changes ONLY the AVD cleanup trap: no unconditional `wait` on an emulator parent that remains alive; TERM/poll for at most ~5sec, KILL if necessary, record `out/ksu/cleanup.log` and always return. It does not modify root/permissions/TUN/SSL/DNS protocols. The next current SOURCE must rerun the same single Android16 KSU canary once and obtain a full green Action, preserving earlier functional data and accurate failure history.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct an unbounded AVD EXIT trap that caused overall CI FAIL after actual DNS/TLS/UDP/TCP/SIGKILL PASS; no qualification until fixed-source full workflow SUCCESS."}
```
