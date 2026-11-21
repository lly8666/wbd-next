# KSU AVD runtime bounded after slow runner (2026-11-16)

Source `aec38a1a0fd1c2d8c691d726b24c0dd9f51cb4e2` [Action43826176241](https://github.com/lly8666/wbd-next/actions/runs/43826176241) successfully compiled current Bionic native code and prepared matching KSU AVD, but the manually booted emulator stage remained in-progress far longer than the prior stable ~3-minute KSU run; no SIGKILL cleanup qualification was yet observed. This change retains exactly the same real KSU/Root/App/native/route cleanup semantics and adds: each ADB command 18s deadline; 130s ADB-auth and 210s Android sys.boot_completed per cold boot; an overall 780s real-emulator step ceiling; future branch-scoped CI concurrency cancels superseded test runs. If boot is unhealthy, it will preserve logs/artifacts rather than hang. The older run remains source-specific and no Root watchdog PASS is inferred from it.

```feature-impact
{"kind":"none","ids":[],"reason":"Bound slow Android16 KSU AVD/ADB setup after stalled job; no change to app/root data plane or evidence qualification."}
```
