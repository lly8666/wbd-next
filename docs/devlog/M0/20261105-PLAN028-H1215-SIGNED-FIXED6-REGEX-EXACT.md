# PLAN028 H1215 — scoped native Fixed6 receipt regex corrections

H1214 introduced a new **shared-only** original Windows Fixed6 true SYN/SYNACK MSS, protected original Go TLS record and actual Rust M4 profile6 two-gen/OS MTU proof. Preflight source inspection before its expensive Action showed the Python `r` regexes accidentally contained **26 double-escaped backslashes** (`\\d` rather than `\d`; `[^\\n]` rather than `[^\n]`), which would reject valid two-generation native logs. Correct precisely the 26 pairs in this new proof only. The historical H981 single-session branch and all Go/Rust product bytes remain unchanged. Re-run single opt-in signed Windows Fixed6 `[plan028-win-physical-fixed6]`; do not promote H1214 until entire Action/UDP/TCP/Stop passes. Signed Windows Auto source b315 Action41939489419 is full success; Game4off source4ce still running, native high30 sourcebc5 overall FAIL to investigate.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct test-only raw regex escaping for new Windows shared Fixed6 genuine MSS, record, native M4 and OS validation; preserve old H981."}
```
