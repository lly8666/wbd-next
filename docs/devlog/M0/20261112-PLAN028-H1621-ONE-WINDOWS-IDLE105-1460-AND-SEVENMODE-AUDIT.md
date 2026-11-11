# PLAN028 H1621 | Windows 105s idle source-locked 1460 test vector and seven-mode audit

Original H1620 native Action 43066195581 is **FAIL**. The source8a H1600 Windows EXE/DLL plus Linux Go/Rust ISA-L SHA and signed Npcap/real WSL2 kernel preconditions passed. No original TLS/Rust product business started; actual first cause: requested outer `default1460` with immutable old 105s scenario `tun_mtu=1400`, rejected correctly by `configured_native_test_mtu()` with `outer MTU selector/source scenario mismatch`. The original full artifact ZIP 13876720931 / SHA256 ba9f0a87b778601de85a5d5da5c68cc2cf1e6ddbf5fa5935eca4027a3f4e47f4 and guest boot ZIP 13876690824 / SHA256 90f7d7ab18fd190e93bc97c110e6d4d0ca1f8fdcd35cc4b49653267f265659f5 are preserved. The prior Action must not be promoted to a business PASS.

H1621 corrects only a test scenario: add `scenarios/plan028-h1621-normal-idle105-outer1460-10m25ms0-60s.json`, exact clone of original idle105 Normal 10Mbps both ways / 25ms 0% / 60s plus `scenario_id` and `tun_mtu` changed from 1400 to 1460. Original old scene remains untouched. Wrapper Python preflight compares complete parsed scenes ignoring only the derived `scenario_sha256` then modifies only ID and MTU, and invokes the original OS MTU guard with expected 1460/1460 PASS and old incompatible 1460/1400 expected FAIL. Existing wrapper still requests outer `default1460` and reuses official H1600 Action43027983611 unchanged signed Windows and Linux binaries; no Go/Rust compilation.

One independent Windows Npcap+single Wintun / true Linux WSL2 original Go TLS443+Rust M4 test is dispatched by the existing wrapper (the wrapper is not native evidence). The 105s no-application interval, 60s real duplex application, and final exact Stop remain NOT_RUN until the actual native target and archived result qualify. User-skipped near-inner-MTU and multiple Wintuns on one Windows host remain out of scope.

Parallel source-only seven-mode/default audit: seven Windows public mode choices normal, fixed, auto, game2, game4, game2-fec, game4-fec match Linux Normal Off, FEC Fixed6/Auto, Game2 Off/Fixed6, Game4 Off/Fixed6. Game Auto unsupported. Defaults outer complete IPv4 MTU 1460, Normal/Game FEC Off, cold rotation 0, outer repair on, Game4 copy stagger [0,4,50,140] ms, record cipher ChaCha, TUN queue 2048/fq600. Old SOURCE0cda seven-mode 28 cold rotations, 16219/16220 echoed are OLD-SOURCE scoped; newer SOURCE8a has representative modes but is not a complete new seven-mode network certification. Audit JSON: `docs/evidence/M0/PLAN028-H1621-SEVENMODE-DEFAULTS-SOURCE-AUDIT-20261112.json`.

PLAN028 IN_PROGRESS: independent Windows DUT L3 and other release acceptance unmet. No PLAN029/030.

```feature-impact
{"kind":"none","reason":"Source-locked clone of one test vector and runtime MTU-contract preflight, no product, GUI, protocol or default code changes."}
```
