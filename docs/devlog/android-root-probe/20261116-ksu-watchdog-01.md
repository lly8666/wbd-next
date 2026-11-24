## KSU abnormal-owner-stop canary, same Android16 AVD

Previously proved App ↔ KSU-TUN UDP roundtrip on source `e7d59cf7574d9932a9a24b3b273bb4e5106723b0` / [Action43823818642](https://github.com/lly8666/wbd-next/actions/runs/43823818642). This source forks an independent KSU root watchdog BEFORE opening nonpersistent TUN. A CLOEXEC pipe is the owner lease; after worker SIGKILL its writer closes automatically. Watchdog deletes only exactly verified pref8200 / UID range / synthetic /32 / table235; refuses ambiguous or non-owned rule. Watchdog uses distinct session and closes App stdio; never flushes all Android rules, NAT or default route.

Single KSU CI first proves actual ordinary App UDP roundtrip, then via real KSU shell fixture calls appflow-kill UID TOKEN. Root worker signals READY only after scoped route/rule installation, then self-SIGKILLs; independent watcher must attest orphan rule observed+deleted. CI verifies global route/rule snapshots identical and table235 empty. This qualifies KSU root native worker SIGKILL only, not Android app death, whole process-group kill, reboot or production persistence. No PASS before actual CI.

```feature-impact
{"kind":"none","ids":[],"reason":"Add bounded independent KSU root watchdog and SIGKILL cleanup canary in the single prior Android16 App-TUN AVD; not a product qualification."}
```
