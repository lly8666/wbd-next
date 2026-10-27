# M0 loss1 S5 — preserve real product, correct first-delivery fixture

From test branch SOURCE 6eafe4c58fdefeab11e03c0fc470622f5cd7b766, original tools/m0-v4-public-real-linux-netns.sh script was read at current main alongside docs/testing/NETWORK_TRIAGE.md and docs/architecture/modules/08-RECOVERY.md (overridden by approved opportunistic v3) and latest relevant S432, S474, S478, S485 edits. Original Actions40566375977/1 FAIL: 1% netem caused first 69 echoed UDP packets followed by timeout because the client blocks before offering the rest, native two owners stopped properly, Rust actual firstsend/ACK and no repair. Previous failure is real, not relabeled.

This test-only **copy** of that actual two-netns/Go TLS/Rust raw TUN shell preserves the original exact product executable artifact12760744437 from source33ed20b4, sha256 b0caeea1d953076480a8dd30fb63612194e09668e3b0af41ab6b8f80755e3439. The generated client now offers 512 distinct genuine UDP datagrams paced 3ms *without waiting for echo*, and collects unique replies until 6s drain. It records offered/delivered/missing/duplicates, two real netem qdisc drop counters, M2 owner first copies/ACKs/retransmissions and validates original both-owned Stop. A conservative <=20 missing / 512 coarse two-direction IID diagnostic bound is not formal loss recovery/p99 qualification. Original low-loss v3 does not force a retransmission and no such test assertion remains. Any full run FAIL remains FAIL; no product code, Go/Rust build, TLS/AEAD/PN/repair policy or original shared fixture modification.

One narrow new workflow triggers one real kernel loss1 scenario on independent Linux x64 and **downloads** exact prior compiled binary by run-id=40562809565, with original manifest/SHA cross-check. No new ARM64 job, no recompile, no N0/N1 stress. Feature-impact none: test harness-only, no product behavior or feature-stage change.

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only corrected lossy UDP generator first-delivery receipt and reliable real Stop; unchanged frozen production binary, original red preserved."}
```
