# PLAN028 H1458｜一场四路并行原生压力：真实5客户端、SOURCE548

用户要求“继续，一次性多搞几个，包括压测”。上一场SOURCE548a Win签名Wintun+WSL2 Linux真实600s已完成原始UDP/TCP/Stop且无明显泄漏；但该内核UDP应用实际每客户端约9.3pps，只是低压功能+生命周期 `PASS_SCOPED`，不是100pps、10Mbps或最高FEC压力。正式Windows 1800s仍无独立控制域，不刷种子。

**本次一个Action、四台独立 `ubuntu-24.04` x86_64 Runner并行**，每台拥有6个真实Linux netns、5个各自登录的原Go TLS443/Rust M4客户端，使用同一SOURCE `548a47cc708d82d45e1722540b6677342f3c8c5b` 的[原始产物](https://github.com/lly8666/wbd-next/actions/runs/42555320138/artifacts/13646553865)。下载时强制ELF62及三文件实际SHA256、Go/Rust版本、native ISA-L；脚本等变化只属于测试wrapper，**绝不把新wrapper SHA伪称为新编译产品SHA**。复用以前H1332/H1360/H1349的SOURCE级完整180s True native流量、内核双向UDP/TCP+5份原始Stop和真实CPU指标。四场景：① Normal零损 10→25→50→25Mbps；② Normal零损25→50→75→50Mbps；③ Game4 Fixed6零损3→5→10→20→10Mbps；④ 五模式混合弱网，损伤0/1/5/15/30%，单程0/15/50/100/125ms，保持真实tc netem DATA损伤，静态veth邻居仅是TEST underlay ARP失效隔离（未修改产品）。

普通Normal和Game4每场相互独立，所有预算是**目标**而不是实测；真值从`h1458-capacity-audit.json`按十毫秒真实应用TX/RX桶算实际Mbps、持续秒级空洞、每核CPU/Host busy、generator fill与原始客户端/服务端Stop。低于95%生成目标或宿主饱和单列CAPACITY_LIMITED/NEAR_LIMIT，任何实际无业务或原始Stop失败不因CI绿灯变PASS。弱网真实30%需看原始qdisc、接收、原Go/Rust认证Stop和逐方向损伤/告警；带告警即INCONCLUSIVE或FAIL，不假装弱网交付率。

对源代码只在三对**既有压测测试夹具及审计脚本**新增显式 `WBD_PLAN028_H1458_PRODUCT_SOURCE` SOURCE白名单，默认仍是历史6c5；未改任何Go/Rust产品、TLS/WAL/FEC传输协议或Windows宿主。事前廉价Python源锁与preflight、每场单独artifact、`fail-fast:false`以免先失败者取消其他对照。Windows+WSL2真实600 PASS、ARM64 eef2两条1800 PASS_SCOPED保留，Windows L3 1800 NOT_QUALIFIED，H998历史HOT FAIL、Android/物理NOT_RUN；无PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Four independently hosted original native Linux five-client L2 throughput/loss stresses, exact existing-source Go/Rust/ISA-L binaries, fixture/auditor source-pin opt-in only; no product or protocol edits."}
```
