# PLAN028 H1149 — remove Go-only protected cold parser dependency on FEC2 native type

[H1148 native ARM64/ARM64 Action41836305959](https://github.com/lly8666/wbd-next/actions/runs/41836305959) full original source86a3 **SUCCESS**, artifact13326810720 SHA256 3ef66acc0240882abfc84afe6924fe107e52fd71980f17bfebdc20491d8e95cb. True ARM64 ELF183 client+server+Rust with original Go TLS, protected Normal off/auto/fixed-profile6/off and independent ChaCha/AES128/AES256 ciphers, source-fixed 3 active devices / 4 TLS sessions / one443. Actual kernel UDP70 (routed70/unrouted0), OS inner TUN 1389/1375/1195 and server shared 1389, server/client real Rust fixed6 effective readbacks before old exact and final Stop. H1147 earlier pre-native fixture FAIL remains.

Two other independent Actions41836305960/41836305851 **FAIL at Go-only build**: they intentionally copy admission_v4.go and tests into the original Go donor without optional fec_v2_policy.go; new helper `v4ProtectedNormalFECProfile` wrongly returned a `FecV2Profile` native type that does not exist in cold-only assembly. Exact-source narrow correction: make protected cold helper return `uint8` profile0..6, preserve all authenticated byte22 checks and reject rules, cast the result to FecV2Profile *only* inside the full Linux original native bridge before configuring the same Rust FEC owner, and update narrow test and pinned manifest git-blob SHA. Does not change TLS ClientHello, protected record length (24B), AEAD/PN, packet format or process TUN. H1148 native PASS is SOURCE86a3; the H1149 compiled-source gate has to report separately.

Game2/Game4 mixed with Normal on one shared 443 remains OPEN. Next distinct full Linux task after ARM64/ARM64 is x86_64/x86_64. Hardware Wi-Fi/Android, remote ICMP and CPU causal gain NOT_PROVEN; H998 old same-connection MTU hot shrink FAIL.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Record source-scoped native ARM64 fixed6/ciphers proof and repair cold Go profile type coupling, no runtime wire change."}
```
