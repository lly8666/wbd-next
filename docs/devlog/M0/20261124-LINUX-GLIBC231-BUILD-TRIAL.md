# M0 Linux glibc 2.31 build and trial

Registered increment: docs/decisions/M0-LINUX-GLIBC231-20261124.md. Use the same original Go and Rust/ISA-L release features on native x86_64 and aarch64. The existing dual-ISA builder defaults to the glibc 2.31 environment; explicit host mode is only for A/B. Ubuntu 20.04 userspace smoke shares the hosted runner kernel; physical 5.4 kernel is NOT_RUN. Normal TCP 4-flow 10s A/B/A and process CPU/GiB are scoped measurements, not throughput tuning or cross-ISA comparisons. All validation is NOT_RUN until exact SOURCE results exist. No product hot-path changes.

```feature-impact
{"kind":"none","ids":[],"reason":"Build/link environment and test harness only; no protocol, runtime defaults, product options, data-plane implementation or driver changes. Linux release ABI qualification remains pending."}
```

First SOURCE 23a73e8c23e289d5f5c898faf15560c97a761dac Action 45411561914 ARM64 failed in Docker image preparation: bullseye-security package downloads HTTP404 after LTS EOL, before product compilation. Replace removed floating mirrors with signed Debian archive and final security snapshot. Functional/performance NOT_RUN for that failed leg.

Second SOURCE f38cfc218926b4aea206d88a5ecf2a836ce7be88 Action45411847411: both ISAs passed apt and built/installed libisal.a; last log was make install, no Rust invocation. The immediate next command is nm | grep -q under pipefail; old binutils can receive SIGPIPE on a successful early match. Preserve actual nm result in file then grep it; add missing help2man (make reported ignored errors). Failure mechanism is a candidate until next run; no product or performance PASS.

Third run 45414127999 failed both ISAs after successful ISA-L installation: exact shell error unexpected EOF matching single quote. Prior editor introduced duplicate script tail via replacement-string $' expansion. Reconstruct from f38cfc2 by line splice, verify one build sequence and add early syntax checks before dependency installs. No product or performance pass.

Fourth run 45415625160 SOURCE 32193483a9f5bb962d2ec2ddfa1ea84d2f60b6b6, both jobs SUCCESS. Independently downloaded and checked the two original artifact zip digests, inner tar and six ELF hashes, actual version needs and ISA-L symbols; all six A/B/A legs checked against native app/Stop receipt and receiver bytes. x86 +0.47% goodput/+1.33% process CPU/GiB; ARM +0.26%/-0.77%. Focal userland actual both-direction TCP/UDP and Stop PASS on both; host kernel 7.0, physical 5.4 NOT_RUN. See docs/evidence/M0/20261124-LINUX-GLIBC231-DUAL-ISA-SCOPED-PASS.json. Scope is Normal 4 flows 10s, not FEC/weaknet/P99. Adopt shared dual-native builder as Linux delivery entry, not archival fixture-only builds.

Integration maintenance 45417245306: 832 tests, exactly one stale H982 source assertion expected waitForOriginalColdSYN(dialCtx,assoc); main H2408 intentionally split SYN/TLS deadlines and now uses synCtx. Update only the fixture to verify original retry and ordered separate deadline scopes, no product or build change. Feature catalog 45417245367 PASS. Preserve all other prior product failures/physical NOT_RUN.
