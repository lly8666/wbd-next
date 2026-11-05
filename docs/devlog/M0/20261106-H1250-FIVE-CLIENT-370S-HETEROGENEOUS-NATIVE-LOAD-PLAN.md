# PLAN028 H1250 — five concurrent native clients, 370s heterogeneous load

User request: diagnose sustained throughput/backpressure and unfairness under large concurrent flows, different client network configurations and physical loss for >5 minutes, following H1247 bounded shared-TUN queue fix.

One fresh x86_64 Linux Action and exact-source original Go TLS/Rust M4 build (pinned original Go donor a7a82db, local SOURCE sha/three binary hashes). Dedicated Linux namespaces: one server on TLS port443, ONE real shared Rust TUN reader, five independent authenticated installation leases. Modes and user choices: A NormalOff/AES128/outer1460; B NormalAuto/ChaCha/outer1460; C Game2Off/AES256/outer1460; D Game4Fixed6/ChaCha/outer1460; E NormalFixed6/AES128/outer1280. Per-client kernel physical netem on BOTH peer egress directions: 0/1/5/15/30% loss, 0/15/50/100/125ms one-way. Readback qdisc drop counters; no application-level retransmission in UDP harness.

Ten real application workers (server and client for each lease) using repository network_harness/traffic.py; one Linux monotonic start_ns, coordinated simultaneous first UDP. First two client pairs also exercise true framed TCP traffic (20% target), other three predominantly high PPS UDP; distinct integrity-checked sequence bodies 256/1024B. Probe 2Hz, one-way delivered-only latency, RTT, per-10ms telemetry. 10s warmup at 30% demand, 60s initial 60% demand, **240s full 192Mbps aggregate bidirectional offered target**, 60s overloaded 130% target (about250Mbps), **370s traffic plus10s drain**. CPU/RSS by per-process /proc every3s, OS TUN/underlay readback, original Rust shared-TUN drop counters upon real Stop. Each client's 30s sustained throughput windows and diagnostic alerts distinguish sender pacing/bottleneck vs kernel intentionally injected loss vs path/queue stalls.

The action marks DIAGNOSTIC_COMPLETE only after all ten workers finish and report source-locked 370s data and positive real loss injection; a successful data collection **does not qualify throughput, p99, CPU causality, physical multi-host, ARM, Windows or absolute zero loss**. Alerts are recorded even when collection succeeds. Native tool/CI additions only; no runtime code, crypto, protocol, MTU defaults or FEC semantics changed. If any client cannot complete genuine TLS/product attach or application setup, fail and retain partial artifacts rather than fabricate throughput.

Workflow: `.github/workflows/m0-plan028-h1250-five-client-370s-native.yml`. Native orchestrator: `tools/m0-plan028-five-client-370s-netns.py`. Reporter: `tools/m0-plan028-five-client-load-report.py`. Evidence requires SOURCE, Action, manifest/hash and report artifact. H1247 latest queue recovery unit 4/4 PASS is separate; H998 same-socket MTU shrink historical FAIL not relabeled.

```feature-impact
{"kind":"none","reason":"Testing-only native network performance diagnostic harness and scoped telemetry; no feature or runtime behavior change."}
```
