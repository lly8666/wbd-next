# PLAN028 H1077｜ARM64双端 Game4 FEC6 原生八条 TLS 首飞和真实切网

按用户最新整任务平台轮换，本轮Linux完整任务是 **ARM64原生client + ARM64原生server**，不用QEMU/异构client-server。H1076 x86 Game4FEC6八lane真实TCP首飞/源IPv4切换已有限定PASS；现基于H1075已实际通过的同一原 Go+Rust Ubuntu-24.04-arm source装配流程，追加独立单一 Game4 fixed6 真网络场景。构建一套 ARM64 原Go TLS与Rust M4，一组Game4的原4路+新源IP的4路，双方仍共享目的443。

必须同时取得8条独立的真实SYN/SYNACK与ClientHello/ServerHello TCP重组，32B HMAC兼容SessionID每lane各不相同，服务器在首ClientHello前零载荷，未注入WB-R1，应用专用CA+32B离线路由key+账号密码，旧M4精准Stop后新TLS认证、原租约不变、外层默认1460/新物理1280→Rust内层预算/OS读回、旧新各5个真实UDP及parity copied>0。PCAP仅留在runner，上传脱敏审计/结果JSON。

新工作流 `.github/workflows/m0-plan028-tls-game4-native-arm64.yml`，不会重跑七模式、旧027矩阵或吞吐。**当前SOURCE候选/尚未运行**；H998在线缩窄旧FAIL、旧ARM64 Game4FEC Action FAIL、CPU/p99、远端ICMP、Windows实际网卡、Game健康A→A+B→B同存仍保留历史限定。即使本次成功，顺序old Stop→new TLS只能证明已断后的直接恢复。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1077 native ARM64 both endpoints exact original Go/Rust standard TLS Game4FEC6 eight old/new TCP ClientHello and sourceIP/MTU recovery one-source one-scenario candidate."}
```

## H1078 原生 ARM64 SOURCE 审定

[Action 41751006793](https://github.com/lly8666/wbd-next/actions/runs/41751006793) SUCCESS，工件13286615433独立解包九份文件并核SHA256（详见 `docs/evidence/M0/PLAN028-H1078-SOURCE6563-NATIVE-ARM64-GAME4-8-TLS-20261104.json`）。本地/真实ARM64原 Go TLS+Rust Game4 fixed6 两代4+4条TCP的SYN/SYNACK、ClientHello首载荷667B、ServerHello首载荷127B、各自32B互不重复SessionID、服务端提前载荷0/无WB-R1；出口源IP .2→.3、OS TUN MTU1178、5+5实际UDP、旧Stop与新组FEC均限定PASS。**仍非完整Finished/基线指纹、Windows真实网卡变更或Game健康lane重叠PASS**。下个新Linux工作包x86双端。
