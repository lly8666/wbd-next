# PLAN028 H1501: two current-source ARM64 long tests collected; new Windows signed 600s

Base 3cbe6032b0786ffc280b282483be15ea342a0046 / M0 H1500. Both 1800s original native ARM64 five-client scenarios are already completed SUCCESS; do not rerun ARM:
- H1498 https://github.com/lly8666/wbd-next/actions/runs/42738333653 original ZIP 13729227737 sha 2bfbf211c516b0991f4791e9b504250fdaff7a13f81ea20a518368add42b3fef CRC PASS. Genuine 1800s underlay 0/1/5/15/30%: 58 independently verified authenticated Normal B promotions; 0 B_UNPROVEN; all six exact owned Stop; strict original gate PASS_SCOPED. Erin 30% residual uplink/downlink 2982/3091, Carol5% 6964/6948 kept, zero-loss users 0 missing.
- H1499 https://github.com/lly8666/wbd-next/actions/runs/42738333604 original ZIP 13729287748 sha 12eb98c02bbc80a7d1e6d938765821fdef227673a7a558239a553d3c52e861ac CRC PASS. Genuine 1800s underlay 0/0/1/1/5%: 69 authenticated Normal B promotions, 0 B_UNPROVEN, all owned Stop, strict PASS_SCOPED. Carol1% residual 176/149 retained; all zero-loss users 0 missing.

User explicitly requests Windows 600 alongside ARM long. ARM long happened and finished, so run Windows current Health5 source now rather than claiming old source548 H1457 passes current release. Source1211fd... ARM Go/Rust native product differs only by CI/docs from current main3cbe; new Windows+Linux workflow builds original signed Windows Npcap1.88/Wintun0.14.1 client and independent WSL2 native Linux TUN client/server from new GitHub SHA, same real TLS443, with mandatory live 600s UDP/TCP, resource/mgmt, exact Windows Stop then Linux surviving TCP/UDP, Linux/server final Stop, WSL2/WAL/NPF cleanup. Marker [plan028-win-linux-co-client] [plan028-win-linux-600] triggers known historical full native workflow only for one 600s product session, plus clean Windows750 control and Ubuntu offhost metadata witness. Historical real app rate is ~9.3pps, not high PPS capacity; 1800 independent Windows device qualification still missing.

At commit Windows new 600 is NOT_RUN pending automatic Action. Preserve previous H1457 old source scoped PASS, source66fb old 600/1800 failures, H1492 original Erin unproved FAIL, H998 hot MTU FAIL, Android/physical NOT_RUN. PLAN028 IN_PROGRESS.

```feature-impact
{"kind":"none","ids":[],"reason":"Exact signed existing Windows600 trigger and current ARM original artifact collection; no product/wire change."}
```
