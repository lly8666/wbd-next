# M0 Linux glibc 2.31 build and trial

Registered increment: docs/decisions/M0-LINUX-GLIBC231-20261124.md. Use the same original Go and Rust/ISA-L release features on native x86_64 and aarch64. The existing dual-ISA builder defaults to the glibc 2.31 environment; explicit host mode is only for A/B. Ubuntu 20.04 userspace smoke shares the hosted runner kernel; physical 5.4 kernel is NOT_RUN. Normal TCP 4-flow 10s A/B/A and process CPU/GiB are scoped measurements, not throughput tuning or cross-ISA comparisons. All validation is NOT_RUN until exact SOURCE results exist. No product hot-path changes.

```feature-impact
{"kind":"none","ids":[],"reason":"Build/link environment and test harness only; no protocol, runtime defaults, product options, data-plane implementation or driver changes. Linux release ABI qualification remains pending."}
```
