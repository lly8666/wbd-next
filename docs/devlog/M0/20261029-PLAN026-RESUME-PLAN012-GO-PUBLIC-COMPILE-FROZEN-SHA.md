# M0 PLAN026 test resume 2026-10-29 — source-exact PLAN012 and strict frozen source assertions

Main source `e82be50d`:
- Action `40832034946` exact-source Windows original-Go TLS Rust+signed Wintun WAL **SUCCESS**: Game2/4 scoped kernel first/reverse/Stop, Fixed+Auto RS16 missing original source recovery.
- Action `40831544826` Linux original-Go TLS Fixed real kernel Applied **SUCCESS** at source `64ead9e3`.
- Action `40832035027` PLAN012 genuine Linux combined gate **FAIL** only after Rust Game2/4 original TLS and original Go Game real TUN app succeeded. Go public CLI compile errors: `RawIPv4Endpoint.ExcludeDetachedData` and `SetPublicV4AdvertisedMSS`/`PublicV4AdvertisedMSS` symbols missing. All are implemented by actual current overlay `r0/go_overlay/internal/faketcp/raw_detached_data_linux.go` and `public_v4_mss.go`, but its one-step frozen donor staging omitted those two files. Install exactly those current overlay files into the real legacy Go staging tree with existence and byte equality guards, not stubs, not a substitute binary, no test skipping.
- Same-source governance regression `40832034833` fails **three** static assertions, because exact live M0 manifest now holds 41 operations/21 created files (M4 37/17 plus four source-locked Windows Native IO files), and M0 runtimeentry's current Git blob is `e5dbe438...`, not the earlier current override `948ff4c1...`. Preserve all 34 historical frozen Git blobs, explicitly authorize **only** the two changed current SHA pins, assert exact four appended M0 files, all original 37 donor entries and current blobs. No relaxed source checks or product mode PASS.
- Latest PLAN012 strict Rust test counts remain 4 original native live RX tests and 5 Fixed stream tests; no assertions or source unit tests are removed.

Expected: same-source PLAN012 Linux combined real Go product compile should progress to subsequent full real TUN kernel test, historic frozen guard should become PASS, but no final status is claimed before new CI.

```feature-impact
{"kind":"none","ids":[],"reason":"CI source-locked original-Go public Linux V4 staging adds existing native faketcp source and frozen overlay tests retain historic SHA with precise M0 authorized current source/manifest hashes; no product wire or policy changed."}
```
