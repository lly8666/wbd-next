# R2-M2-PLAN008-MATURE-FIRSTSEND-FEEDBACK-011

Authorized by main registry rev2 epoch1 against PLAN-008 §1 M2/§3/§4; prior 010 H 9b70e35 still valid. This is an owner-local event-quality **observation**, not a second controller or recovery/loss engine.

New typed ingress in crates/wbd-recovery/src/maturity.rs accepts FINAL definite kernel first-send DATA bytes, definite NotSent, Uncertain, independently authenticated reverse receipt with pinned scope, and possible repair/FEC source events. It emits separate 2s/8s mature histograms with conserved actual-firstsent denominator; missing requires an explicitly covered negative bitmap; unreported/lost feedback is uncovered not clean. Positive after repair/possible FEC is ambiguous attribution, not line success. Event timestamps lock outcomes to the original maturity deadline even if owner polls late; late ACK may affect 8s but never rewrite 2s. No RX packet count feeds denominator.

Bound: max_live_data<=200000 owner-configured, each accepted record at most two BTreeSet timer nodes, one BTreeMap entry; at most 64 nodes processed each poll and no per-packet Go callback. Capacity overflow increments explicit censored count+wire bytes and MUST make controller interval unusable for a loss-rate estimate. Stop clears all index nodes, rejects old generation callbacks; fresh creates a new owner bound to M0-pinned route. System clock is injected, never read. No changes to RACK, two same-cipher repair attempts, quota, sparse global exception, PN, encryption, socket, wire or client controller.

Source awaiting native Actions; Go actual send/AEAD, real latency/p99/platform still NOT_RUN.
