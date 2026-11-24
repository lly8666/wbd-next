# M0 Linux glibc 2.31 build and trial

Registered increment: docs/decisions/M0-LINUX-GLIBC231-20261124.md. Use the same original Go and Rust/ISA-L release features on native x86_64 and aarch64. The existing dual-ISA builder defaults to the glibc 2.31 environment; explicit host mode is only for A/B. Ubuntu 20.04 userspace smoke shares the hosted runner kernel; physical 5.4 kernel is NOT_RUN. Normal TCP 4-flow 10s A/B/A and process CPU/GiB are scoped measurements, not throughput tuning or cross-ISA comparisons. All validation is NOT_RUN until exact SOURCE results exist. No product hot-path changes.

```feature-impact
{"kind":"none","ids":[],"reason":"Build/link environment and test harness only; no protocol, runtime defaults, product options, data-plane implementation or driver changes. Linux release ABI qualification remains pending."}
```

First SOURCE 23a73e8c23e289d5f5c898faf15560c97a761dac Action 45411561914 ARM64 failed in Docker image preparation: bullseye-security package downloads HTTP404 after LTS EOL, before product compilation. Replace removed floating mirrors with signed Debian archive and final security snapshot. Functional/performance NOT_RUN for that failed leg.

Second SOURCE f38cfc218926b4aea206d88a5ecf2a836ce7be88 Action45411847411: both ISAs passed apt and built/installed libisal.a; last log was make install, no Rust invocation. The immediate next command is nm | grep -q under pipefail; old binutils can receive SIGPIPE on a successful early match. Preserve actual nm result in file then grep it; add missing help2man (make reported ignored errors). Failure mechanism is a candidate until next run; no product or performance PASS.

Third run 45414127999 failed both ISAs after successful ISA-L installation: exact shell error unexpected EOF matching single quote. Prior editor introduced duplicate script tail via replacement-string $' expansion. Reconstruct from f38cfc2 by line splice, verify one build sequence and add early syntax checks before dependency installs. No product or performance pass.
