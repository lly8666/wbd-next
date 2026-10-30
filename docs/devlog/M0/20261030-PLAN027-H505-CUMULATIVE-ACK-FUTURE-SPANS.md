# PLAN027 H505: bounded authenticated future interval coalescing, real ACK bottleneck

Recovered H503 **four completed** source0b7391 genuine native 50Mbps per direction, 150ms one-way, 60s 1/5/10/30% tc loss independent Actions 41039752111/41039755447/41039758730/41039762110. Full F/R/C and artifact ZIP hashes in [H503 evidence](../evidence/M0/PLAN027-H503-RECOVERED-H501-LIVE-REPAIR-AND-TIER-20261030.json). All four original TLS + signed NPF/Wintun ↔ Linux raw/TUN, offered >=~50M both and true tc drop/owned Stop PASS. At 1/5/10/30%, Windows R/(F+R+C) ~1.24/1.10/1.19/1.12%, Linux R/F ~6.35/5.44/6.56/6.80%. **Measured grader is NOT healthy**: loss tiers not correlated with true loss; never claim parity or force extra resend to 8% by budget.

Production issue from H501 original native source: Linux `OriginalPresentationAck::verified` and Windows `PresentationAck::verified` saved one **per-record future interval** behind a real missing cumulative TCP byte; after only 256 authentic later records both stopped recording, even if lost record subsequently arrived, causing permanent stale cumulative feedback. H505 on both ends coalesces overlapping/adjacent verified byte spans into at most 256 disjoint intervals, preserving authenticated-only advancement and exact seq32 extension; no need for 600-record heap or new per-record worker. Each side has a focused >256 contiguous future records regression: after missing real range arrives, cumulative ACK reaches end and state frees. Not a wire SACK handshake or claim to recover irrecoverable first gap.

Old Go source a7a82db3 actually supports negotiated TCP SACK during SYN/SYN-ACK (`internal/faketcp/client_association.go`, `association.go`), but current Rust-native Go handoff does **not** propagate it; Win `parse_ack_packet(...,false)` and Linux/Win `on_feedback(...,&[])`. H505 does not guess SACK is negotiated, does not fabricate later positive ACK, retains one-shot unmodified ciphertext and smoothing R<=0.10F. Need actual native cold capability + bidirectional real SACK to restore loss-correlated repair on stalled cumulative ACK, or report the low-ratio limitation and leave user scope unfinished.

New SOURCE tests **NOT_YET_RUN** at this code/devlog commit. Run full actual two-OS Windows+Linux source build Action once and real 5% scene; then use frozen binary manifest for 0/1/10/30 and verify authenticated ACK true progress, source STOP, R/F and R/(F+R+C), initial p99, original tc, CPU. H504 same old-source 0% Action41040914488 in flight at creation; preserve result separately.

PLAN027 A4 (120s downshift), A5, B lifecycle, Game2/4 replacement after canceled H499, C capacity/5-minute stability remain unfinished.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"H505 actual Rust Windows/Linux authenticated future ACK spans coalesce; distinct from source0b measured H503 tier results; new binary/real Windows-Linux proof pending and SACK negotiation still absent."}
```
