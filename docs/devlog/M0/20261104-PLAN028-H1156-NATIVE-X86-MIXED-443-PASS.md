# PLAN028 H1156 — original TLS one443 Normal+Game2+Game4 native x86 scoped PASS

[H1155 Action41853631826](https://github.com/lly8666/wbd-next/actions/runs/41853631826) **SUCCESS** after original sourcec44f553 full native x86 ELF62 Go TLS/Rust assembly+hash and protected mode/cipher Go tests. Artifact13336423623 digest sha256:d275d167533b76fce6a93590e4b2bc4b7de91289b93b481ef939f4485b61012d. One server443, three distinct authenticated /32: Alice Game2 FEC off ChaCha client TUN1373 real12 UDP, Bob Game4 fixed6 AES256 TUN1358 real18 UDP, Carol Normal auto AES128 TUN1375 real18 UDP; shared server TUN1389 unchanged, one original Rust kernel reader. Total 48 actual application UDP, Alice Game2 Stop did not interrupt Bob/Carol six post-Stop echoes each, final reader Stop. No private pre-TLS exchange or new DATA routing header.

H1154 Action41848636350 old source6e433 had Go/Rust build and mixed protected policy unit PASS but server rejected `--mode shared` at stale runGame dedicated lanes guard before raw native; retained separate FAIL. H1155 correction opts shared server lanes=0 into existing runGameMultiServer, standalone Game2/4 untouched. Another auto same-source Game4 Action41853631789 SUCCESS, not copied into 48 UDP result. This is a real x86 mixed mode PASS, not all seven modes or ARM mixed qualification.

Next entire Linux task ARM64 client+ARM64 server, never cross-ISA/QEMU; Windows not counted. H998 same-connection online MTU hot shrink historical FAIL, old ARM Game4FEC Action FAIL, physical Wi-Fi/Android/remote ICMP/precise notifier-to-TLS/CPU causal limits remain.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Register one original Go TLS/Rust single443 x86 protected mixed Normal/Game2/Game4 FEC6 48 real UDP, sibling-safe Stop and OS readbacks PASS."}
```
