# H2380 — CN final delivery record

H2378 initial Windows build found one unused import after moving the canonicalizer; H2379 removed it and used the explicit Rust keyword string slice. Current exact product build f0e8e5a2152d05ecd2ec1308eb650e0d0142ebad run 45338373098, independent Windows and ARM64 jobs. H2380/H2381 only compact feature catalog entries and preserve the product tree, no duplicate release build. Earlier run 45338271563 Windows compile failure is retained. Previous main H2376 native dual ISA 45335657114 both PASS. No additional performance or threading work. Do not claim release until real archive and tests pass.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback"],"reason":"Compact existing CN snapshot and GUI update feature records; product scope remains the H2378/H2379 candidate; builds pending."}
```
