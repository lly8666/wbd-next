# M0 real pinned Go V4 TLS → native Rust owner test-only probe (2026-10-15)

Main CODE b23cf780d36042612a1f21a05c8062226b7748a6 builds a non-public Go owner hook (in V4ServerOptions) called ONLY after actual protected credential/exchange/ColdSnapshot and FakeTCP exact Prepare, then commits only after protected reply+Detach. Failure before commit aborts Go epoch and prepared Rust candidate.

Rust builds real M1 ScopedOwner in a separately allocated Rust generation behind TEST-ONLY feature m0_v4_probe. Tagged cgo Linux Go adapter calls actual Rust CDylib from pinned legacy Go TLS peer session. Positive real TLS to Rust candidate tested twice, fresh IDs, stop/release and malformed/fake snapshot negative. The ordinary no-feature Rust CDylib native `nm -D` proof checks no wbd_m0_test_probe_* symbol leaks into production. Rust FFI methods are deliberately NOT authentication and do not enable product.

Original private Go bridge first test expected abort on rejected Prepare (no owner was created), which was an invalid assertion; corrected at 3179144 and real Go TLS12/12 run38707227117 SUCCESS. Exact source b23cf780 native Action38708333395 SUCCESS build+consume, Rust1.85.1/Go1.23.12, pinned legacy a7a82db3; one actual Go TLS->Rust in-process test and one Rust owner-phase negative pass, with two distinct Rust generations within Go test. Artifacts SHA256 digest in adjacent JSON. Same-source main Governance38708333353 SUCCESS. Test-only initial run38707920138 SUCCESS; original failures retained.

Actual early payload copies, Rust cryptographic owner keys/PN, positive trusted production admission, held M4 driver lease and actual business E2E B01–B04 NOT_RUN. FEC positive remains disabled, public C ABI still features0, raw/physical/500Mbps/native WinARM NOT_QUALIFIED. Do not equate in-process smoke with product Go→Rust activation.

M0 next action: actual owner data and hard negative authorization path, consume M1 staged early RX and M4 driver lease once worker-native S/H accepted, then join Go+Rust true B01–B04. No premature new worker assignment; current registry wave M1/M2/M3/M4 already active.
