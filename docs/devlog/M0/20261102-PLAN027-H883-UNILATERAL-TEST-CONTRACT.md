# PLAN027 H883｜H882 unilateral 105 source gate precise rejection

- H882 SOURCE4363 Action41394996188 stopped in the CHEAP fixture-contract job before Linux build, signed Windows DLL, Wintun/NPF or original Go TLS. All H882 source test fields parsed and new unilateral negative test passed; old 20s bilateral fixture regression also demanded 105s-without-direction throw generic `BAD_BLACKHOLE_LIFECYCLE`. New safer parser correctly rejects the 105s-without-direction input with `MISSING_UNILATERAL_DIRECTION`; old test compared only the error text and therefore failed. This is **fixture unit FAIL; real Windows unilateral business NOT_RUN**.
- H883 changes that one legacy test expectation to the explicit fail-closed rejection (still rejects a 105s outage without a direction). Does NOT broaden the allowable scenario or alter any netem, WFP, Health, Go/TLS or Rust owner behavior.
- After the corrected cheap preflight, one signed original Windows↔Linux Action is selected by the existing exact marker `[plan027-h882-win-c2s105]`, same source-controlled 105s **Windows→Linux only** owned IFB outage, true positive IFB kernel drop proof, restored120s business, fresh source binary/Go TLS/Rust native and both Stop. No parallel restart of H880 loss30 pair or H881 Game2 OFF scene, which retain their own in-flight sources.
```feature-impact
{"kind":"none","ids":[],"reason":"Only align the old negative fixture's expected error code with the narrower explicit Windows→Linux 105s guard; actual product and test scenario unchanged."}
```
