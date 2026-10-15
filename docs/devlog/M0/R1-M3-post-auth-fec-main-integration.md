# M0 · R1-M0-M3-POST-AUTH-FEC-MAIN-013 · 2026-10-15

Prior authoritative M0 main HEAD bb21b388 cursor48 evidence S540bdcb8 Governance38671831389 SUCCESS. All four worker branches unchanged; previous work individually accepted and no new worker results inferred.

**Formal third-wave assignment** CODE SOURCE e6edc9a2095942164de9c928a617d356b4c5efae, Governance38672746829 and G2 38672746821 SUCCESS. Registry revision2 epoch1, roles and allowed paths unchanged. M1 STOP-LOAN-GENERATION-006; M2 RECEIPT-REVERSE-SCOPE-005; M3 FEC-MULTISCOPE-012; M4 AF_PACKET-PREFLIGHT-006. See docs/decisions/M0-parallel-worker-atoms-2026-10-15-wave3.md. Assignments authorize work, not automatically executing any worker.

M3 worker code SOURCE42382c60ee51689d49c480411af3df2acc9e9a7d, genuine AEAD+PN replay-before-FEC tests 85/85 Actions38669822925, cursor-only Hf56a6720 Governance38670975617 SUCCESS. M0 imported its typed FEC admission module and tests, added actual main kernel UDP receive test and updated exact codec native CI selector counts from 75 to 85 plus kernel integration count from5 to6.

Main CODE SOURCE **f2ce2d7602a38d6cb494560f8a095cb6270a99f3**: exact **16/16** triggered Actions SUCCESS, including [record auth38673082193](https://github.com/lly8666/wbd-next/actions/runs/38673082193) **85/85**, [FEC retirement38673082408](https://github.com/lly8666/wbd-next/actions/runs/38673082408) **85/85**, and [Linux true sendmmsg/recvmmsg38673082376](https://github.com/lly8666/wbd-next/actions/runs/38673082376) platform **42/42** plus M0 integrated **6/6**, Governance38673082373 PASS. Compiled-once binary/artifact SHA digests are in evidence JSON; cross-ABI38673082179 is **build/inspect only** and does not establish Windows/ARM native runtime.

New main case uses M1 frozen real sealed AEAD record -> actual Linux kernel UDP send+receive -> strict full IPv4/TCP parser -> FEC gate without trusted V4 session origin, repeated `AbsentOrigin` fails before packet mutation/PN replay/FEC accounting. Separate real AEAD lane replay opens same ciphertext PN0 and delivers first business. M3 positive `FecOrigin` constructor is `#[cfg(test)]` only, **not production**. Thus real product FEC cannot currently be enabled; no invented exporter.

The evidence blob was first rejected in a larger write request by a safety check; main remained unchanged; a smaller single-file evidence commit recovered it. Subsequent S updates and cursor-only H must be independently checked on remote.

Product phase R0_FOUNDATION_IN_PROGRESS; Go V4 trusted cold session origin/epoch/direction/lane/generation handoff, AF_PACKET raw TCP, Windows/ARM native, sustained500Mbps/p99 and physical remain NOT_RUN. Next M0 narrowly review real legacy Go V4 provenance and write a fail-closed trust handoff contract; M1–M4 worker atoms independent.
