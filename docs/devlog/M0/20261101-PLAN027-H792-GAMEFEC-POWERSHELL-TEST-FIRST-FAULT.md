# H792 — actual H791 Windows first fault was PowerShell parse, not GameFEC

User priority Actions test execution first, then Game Mode FEC. H790 actual Windows native Win32 TEST-NET-only /32 original PnP + safe receipt CAS Action41311494957 PASS, real ZIP13085128154 downloaded; no host-global WFP//1.

H791 source `9a95bd8a1a475ad020abc322e5e928954c7f280a` original native WAL Action [41312346860](https://github.com/lly8666/wbd-next/actions/runs/41312346860) **FAIL**, original job124865177801. The exact test stage did NOT run: original Go assembly compiled, Rust native DLL release compiled, official Wintun 0.14.1 hash/signature PASS; the next PowerShell step failed immediately while parsing `tools/m0_plan020_native_live_windows_ci.ps1` at line78 Python `root=pathlib.Path.cwd()` due to prior injected line71 containing an unterminated single-quoted test selector `'-test.run=^TestM0PLAN027WindowsRealOriginalGoGame2Fec6SignedWintunFirstReverseStop`. The rest of the intended H791 test invocation had been truncated, leaving a later embedded Python here-string misparsed. This is an Actions test-infrastructure regression, **NOT** original Game2FEC6 negative evidence. Always artifact13085583518 uploaded 12 scoped source artifacts, no new FEC result. H791 Governance41312346905 and maintenance41312346742 SUCCESS.

H792 reconstructs the complete target native test invocation, local log readback and exact required PASS marker without a risky unmatched EOF quote. Adds a Windows PowerShell AST `Parser.ParseFile` gate in main original WAL Action **before** Go/Rust expensive source build; no more late parser surprise. Preserves all five existing scoped modes, original native WAL regressions and no fake GameFEC PASS. New Windows run must be checked for first real Go TLS Rust FEC/Stop failure; do not start 480s global host route capture.

```feature-impact
{"kind":"none","ids":[],"reason":"Repair truncated original PowerShell test harness line and add source-scoped AST parser gate before expensive Windows build, production unchanged."}
```
