# M0 PLAN020 S631 — finish missing native V4/Rust portable product bytes before live OS test

Source S628 `fd5e1e4b6d7ad44195b82548c420d61aa1dfea73` Windows2022 native Action39597711102/1 PASS_SCOPED linked original-Go public V4 TLS Rust M1/M3 packet pump, signed Wintun exclusive native ring and five-stage OS WAL; only Go build and WinForms fake child. H230 current main c85919b4dff48185e2b911a5280aeb90dfa0fc91 Governance39599702131/1 PASS, registry rev3 epoch1 M0 sole main writer. User explicitly wants gates exposed, missing native Rust DLL and V4 executable completed and tested rather than endless edge probes.

Implement ONE SOURCE portable package:
* build real native Rust1.85.1 `wbd_engine.dll` using pinned Cargo.lock + `m0_v4_embedded_go` Windows x64 MSVC;
* package actual `-tags wbd_v4_embedded_go` Go `wbd-client.exe` instead of untagged V3 binary; preserve exact .exe/.dll hashes and source-locked release receipt;
* point real original WinForms `ClientSession.StartAsync` to `--native-v4-product`, consume ONLY independently OS-verified `WBD_WINDOWS_OS_APPLIED` and exact `WBD_WINDOWS_NATIVE_DISCONNECTED_V1` receipts; reject GUI READY or child exit after Applied as sufficient proof.
* run one Windows2022 exact-source Rust DLL + original tagged Go + WinForms bundle build, inspect DLL actual exports, GUI fake-child cannot authorize release. Source-lock all manifests; no frozen M4 or original-Go mutations.

Global persistent WFP and default /1/DNS IPv6 MTU OS changes can strand a shared hosted runner; source-wide release ON only after verified isolated native Windows runner runs real Apply/Recover/Stop with original credential TLS authenticated Rust M3 app both directions plus wrong-owner/stale/crash. On hosted CI keep this OS mutator off, preserve unverified statuses, FEC2/Game OFF. Turn native V4 product **build/start choice** on, not untested OS policy ON.
