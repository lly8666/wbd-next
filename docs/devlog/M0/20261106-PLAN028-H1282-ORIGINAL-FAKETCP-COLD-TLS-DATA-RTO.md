# PLAN028 H1282 — 原生ARM64验收及 FakeTCP 客户端冷 TLS RTO 修复

2026-11-06。H1281 [Action 42214816445](https://github.com/lly8666/wbd-next/actions/runs/42214816445) SOURCE `0eba38f4835323aed4b44f00174e1127d00de048`：原始Go/FakeTCP TLS + Rust M4，三场各1800s五真实认证客户端。build、baseline **PASS(0告警)**；heterogeneous **FAIL(4)**，pressure **FAIL(6)**。已逐份校验三原始ZIP SHA256，详情 [证据JSON](../evidence/M0/PLAN028-H1282-H1281-ARM64-3X1800S-20261106.json)。无服务端Game2整组缺失的老百秒断流，Normal成功本地READY均已匹配服务器独立M4。仍不能从一组试验证明永不复发。

异构/高压Game4服务端真实热lane成功分别6/7次（目标至少10），冷TLS候选超时8/7次；Erin Fixed6 30%物理TC损伤仅8/9代成功（目标至少10）、冷候选超时38/32次，真实上/下行活跃发送无接收空洞2290/1260ms、1380/2290ms。高压Bob/Dave服务端每租约TUN overflow23/50，继续FAIL；CPU一个核百分比67.456/83.355/103.493%，峰值RSS 180332/187592/222288 KiB。真实加密record Accepted R/(F+R)仅0.69536/0.94806/0.69377%，不含控制C、FEC parity、完整IP/TCP/L2字节。

**新发现的直接代码缺口**：原 `faketcp.ClientAssociation.EmitRetransmitDue` 能用原 Sender RTO 重发TCP SYN/已发TLS DATA，但Normal实际只在 `waitForOriginalColdSYN` 的SYN阶段调用它。进入原同步 `native.ConnectAuthenticatedPeer` 后，客户端未驱动Sender DATA retransmit；Game初始和Game4热lane只调用 `WaitEstablished`，连已有有界SYN重传都未驱动。服务端反而有 `table.EmitRetransmitDue` 周期扫描。这是源代码事实，但仍需真实H1282弱网试验判断改善幅度。

H1282在原Go Linux cold路径增加单独有限范围ticker（100ms检查，是否到期由原Sender的1s RTO/原seq/ACK/窗口/副本决定）；严格只在 original FakeTCP `Established` TLS阶段；Detach/Stop或上下文结束立刻退出，不代理M4业务、无额外密文/PN/协议字段，原TLS15秒截止不变。Game2/4每条初始及Game4热候选的SYN使用已有 `waitForOriginalColdSYN` 限次重发，同一条TLS lane逐条各自启用原Sender timer。Go定向测试不制造ACK，丢首次真正Bootstrap DATA，验证相同原seq/payload到期重发及Stop后不再发送；原始产品严格overlay装配锁定Go blob；ARM64 build单测通过后重新三组1800s原生场景。所有业务/换代/队列门槛不变，不将build PASS当产品PASS。

仍开放：30%弱网残余S2C秒级空洞、Game4/Fix6冷候选效果待验、H998 same-socket live MTU FAIL、历史H1259/1268 S2C偶发。未测Control C/FEC parity和全物理IP开销。

```feature-impact
{"kind":"updated","ids":["game-lanes","linux-raw-tun"],"reason":"Original bounded FakeTCP TCP SYN RTO for Game and TLS DATA Sender RTO for all client modes during authenticated cold handshake only; no wire, M4 or FEC changes."}
```
