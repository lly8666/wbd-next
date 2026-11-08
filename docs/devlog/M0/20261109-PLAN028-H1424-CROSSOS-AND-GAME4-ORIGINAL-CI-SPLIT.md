# PLAN028 H1424｜单 Windows + 独立 Linux 双客户端真实通过；Game4 原 CI/业务分账

2026-11-09，恢复 main SOURCE `e6aa4608780e9608070a7313be549a0d4524b38b`；先收在途 Action，不重复派发。详情及 ZIP SHA 见 `docs/evidence/M0/PLAN028-H1424-SOURCEE6AA-WIN-LINUX-ONE443-REAL-SCOPED-PASS-20261109.json`。

- [H1423 原 Windows/Linux Action42502567549](https://github.com/lly8666/wbd-next/actions/runs/42502567549) 六 job SUCCESS，17 原始文件 CRC PASS。原 Windows2025 签名 Npcap/Wintun 单实例 Alice 与独立 Linux netns 原 Go/Rust Bob 同一标准 TLS443 Go/Rust shared TUN server；2账号手动 /32、Windows11/Legacy 分会话 RX。Windows UDP38/38＋reverse36；Linux11/10＋reverse9；两边 TCP PASS。Windows A owned Stop 后 Linux B 又真实收到 10 次 UDP、TCP仍通；Bob/server exact Stop、Win WAL及bridge/原IPv4/路由恢复全 PASS_SCOPED。
- 历史 H1415/H1418/H1419/H1420 原 FAIL 不改：H1420 Linux C2S 236发仅3回、反向229证明 per-session persona/TTL 问题，不是只改报表。后续 H1421–1423 修冷原 SYN 会话→认证后 Rust RX persona 严格匹配，不放松 AEAD/重放/MTU/账号；本次功能业务证明修复有效。
- 同源 [Game4 x86 Action42502567485](https://github.com/lly8666/wbd-next/actions/runs/42502567485) CI FAIL，但原 ZIP12文件 CRC PASS、TLS8 ClientHello无私有前导、A→A+B→B、Game4FEC6 parity、内层 MTU1178/物理1280、新 UDP5、旧Game Stop全部真 PASS_SCOPED。最后 greps 在汇总stdout查只存在被删除的TMP/client.log中的原 `V4_PUBLIC_GAME_REMOTE_M4_PROVEN`，并期待源码从未发出的 `V4_PUBLIC_GAME_TUN_PROMOTED_AFTER_AUTH_RX`。原 Action FAIL 保留，报告错误不能否认真正收发；但单独归档的 B remote M4 positive marker 仍 NOT_OBSERVED，不伪造也不为了报表重跑网络。
- 独立同源 Go标准TLS(x86)、Linux x86/原生ARM64双账号、Windows五模式原生Actions已通过；七档 ISA-L native 源与真实Game4硬件编码历史资格保留。Normal Off此次不需要正 native quanta，不能冒充全模式ISA-L新运行。
- 未完：L0/L1/L2全集和最后受影响SOURCE冻结两场代表1800s综合验收（既有ARM64长测较旧SOURCE），Android/物理机 NOT_RUN，H998旧同socket HOT MTU FAIL。不启动029/030。028保持 IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Recovered real original signed Windows single-client plus independent Linux client co-resident TLS443 protected two-account/business/Stop functionality; separate old CI harness failure retained."}
```
