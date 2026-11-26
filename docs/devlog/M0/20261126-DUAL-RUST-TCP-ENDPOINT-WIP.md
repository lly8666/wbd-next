# M0 dual Rust TCP — endpoint construction WIP

Initial exact SOURCE 105da799ad82b9423d778fd1850bf2503d9909a6: native core run 45803683868 completed successfully, jobs 139853189678 (x86_64) and 139853190101 (aarch64), each 327 tests passed / 0 failed / 0 ignored. Logs attest Rust 1.85.1 and native uname; no product or performance result. Governance 45803683724 and maintenance 45803683656 failed on inherited historical H2416 cursor: old evidence is FUNCTIONAL_PASS rather than the reviewed PASS plus artifact_verified contract; feature catalog and 121 tests passed, full maintenance 832 tests yielded 2 failures and 2 errors rooted in the same stale snapshot. Do not rewrite historical evidence or establish a branch-local cursor; current main cursor H2449 is authoritative. Branch governance remains red pending selective integration against main.

New increment: exact real inner IPv4/TCP headers, checksums, ports, ECN, fixed Rust-derived MTU; separate local CUBIC and middle BBR endpoints; direct receive-ring transfer consumes only bytes actually accepted; actual nonblocking Linux origin connect/read/write, distinct orderly FIN versus abnormal teardown, packet/timer/readiness entrypoints. New tests cover inner packet checksum and a real kernel origin request/response/half-close. All current-source claims unverified until Actions. Not yet wired into the original Normal owner or TUN, no actual product path or performance result. No outer protocol, FEC, old splice, Go FFI or GUI changes. Next integrate actual per-generation flow ownership, readiness/deadline scheduling and authenticated delivery, then native dual-ISA end-to-end.



## Completed exact-source Actions receipt

SOURCE 3e709e0c8577b56ca237a24e6d18fccf998e9965, run 45806924064 attempt 1: both native ISAs 329/329, including checksum and real nonblocking origin socket tests. Both ZIP artifacts downloaded and SHA256 matched, native architecture/source/toolchain/test logs inspected. See docs/evidence/M0/20261126-DUAL-RUST-TCP-ENDPOINT-CORE.json. No full product TUN/authenticated owner, UDP, owned Stop or performance claim. Governance feature declaration FAIL on this source is a documentation error corrected here; maintenance FAIL remains the inherited historical H2416 cursor issue, not a new Rust test failure.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record verified native endpoint-component receipt and preserve product and performance NOT_RUN."}
```
