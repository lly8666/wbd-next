# M4 → M0 integration request: R0 platform harness test filtering

Source `bcf0bcacd51029abe5c8af429a000ee8853ceb3d`; role M4 task `R1-M4-IO-001`; owner of shared file: **M0 only**.

- R1 new worker native workflow `38538117103/attempt1`: exact SOURCE, build/consume successful, **6/6 R1 tests PASS** (5 fake/bounded/borrow, 1 Linux native connected UDP smoke; not AF_PACKET).
- R0 historical platform fake workflow `38538117164/attempt1`: build completed, consume marked **FAIL** despite old 7/7 and new 6/6 assertions all passing: unfiltered same test binary executed **13 passed**. `tools/r0_platform_bundle.py::consume` currently invokes `[binary, '--nocapture']` and requires literal summary `test result: ok. 7 passed; 0 failed`. It therefore fails when new names appear.
- Proposed M0-owned minimal fix: scope that historical invocation to old tests (`[binary, '--nocapture', 'r0_']`), retaining strict comparison against `TESTS` and 7/7 expectation; *do not* relax assertion inventory, change unrelated fixtures, or re-label the existing FAIL as PASS. Run a new exact-SOURCE Actions validation after M0 change and record both the original failure and its replacement.
- G2 constraint: M4 did not edit `tools/`, `.github/`, root Cargo/ABI, M0 docs, or original Go repo. No extra permission requested; M0 can implement the shared harness change. This blocks an all-green R0 workflow but not the separately proven six M4 isolated unit tests.

Native qualification after M4 S: FAKE_R1_PASS=5 tests; LINUX_NATIVE_UDP_SMOKE_PASS=1; LINUX_AF_PACKET/SENDMMSG=NOT_RUN; WINDOWS_NPCAP/WINTUN_NATIVE=NOT_RUN; real OS kernel borrow stop=NOT_RUN; production Normal/FEC-off full crypto/wire/open=NOT_RUN; Go V4=DISABLED.