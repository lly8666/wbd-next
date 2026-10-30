# PLAN027 H538 — 真实同源码0/30%外层机会重传已收口，继续Game/B

**产品 SOURCE `08069b1513a9cba61d0b315dde03505f97ef796c`，并非后续文档提交的HEAD。** 原 Go TLS + Windows signed NPF/Wintun + WSL2 Linux Rust raw/TUN，完整原双端已在 [0% Action41072984387](https://github.com/lly8666/wbd-next/actions/runs/41072984387) 和复用同一原二进制 [30% Action41075416858](https://github.com/lly8666/wbd-next/actions/runs/41075416858) 单场景各60秒成功，审核了 [原ZIP SHA256 95993a1d83cc526a4c0096aba557dcb99ba13acd5e1466d789004103068c3657](https://github.com/lly8666/wbd-next/actions/runs/41075416858)。新场景没有重编Windows/Linux，Linux binary source exact 08069b，GitHub workflow harness SHA d10a915 不可误当产品源码。30%每向10Mbps/250ms，真实内核 loss eth0=30930/ifb=30434，Windows 首到70.0254%，Linux70.0708%，连续每秒新业务，max interdelivery 62/523ms（后者低于长RTT尺度），UDP和TCP真实双方通过、所有者Stop通过。

**外层 F/R/C 原 wire 字节**：Windows F86375024 R303259 C17593（300次），保守不确定重传0；R/F 0.35110%，R/(F+R+C) 0.34980%。Linux F84988535 R149128（180次）、原一包最多一遍，Linux旧停止日志没有独立C字节字段（`NOT_SEPARATELY_EXPOSED`而非伪造0）。Windows影子 `candidate_first=300 expired_first=16094 acked_first=0 repair_accepted=300 shadow_outstanding=0`；Linux `candidate_first=180 expired0=17839 repair_accepted_retired=180 shadow_outstanding=0`，无驱动不确定和等待重投队列。原0%双端 R=0。缺口放弃未逐事件插桩，真实持续有损数百次重发证明机会未因首洞永久冻结；不声称任何单包真丢，也不要求覆盖原业务丢包。Windows原Go+Rust整个进程77.172s观测CPU2.9844s，约单核3.867%，RSS峰值43511808B；**无相同VM前后AB不宣称提升**，Linux full Rust CPU 未单独记录。两侧 Stop 后缓存为空、Linux TUN drop=0。

按用户最新 §0.2，**外层表演式机会重传DONE，不继续比例下限、样本seed/多门限/额外控制包**；额外校准 CPU、恢复率/任意占比不是阻塞门。证据 [H538](../evidence/M0/PLAN027-H538-SOURCE080-TRUE-30P-OPPORTUNISTIC-REPAIR-20261030.json) 与 [H537 0%](../evidence/M0/PLAN027-H537-SOURCE080-TRUE-NATIVE-NOLOSS-20261030.json) 逐项保留。

**恢复其余任务，不重复原场景**：H527 SOURCE7a 的 Game2/4 FEC 被取消，没有合格同源码实测。H538 基于新产品 SOURCE080 的现有可靠 build Action41072984387，派发五个独立原 Windows/Linux 场景：Game2 off 5%、Game4 off 5%、Game2最高FEC 15%、Game4最高FEC 30%，及 Fixed最高FEC 10M/250ms/30%。每个Action一个独立真实测量，沿用已提交的场景与原驱动，不改变产品代码。结果未回来之前不宣称任何 Game PASS。随后 Windows B idle/health/dead/rotate、C混合和突发及 A5 原Go baseline 仍开放；整体PLAN027五项未完全完成。旧H536 200M真实 FAIL 和 H531 Linux生命周期不删。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"记录真实 SOURCE080 双向0/30%同二进制外层机会重传收口和正确限制；后续独立Game/Fixed Actions复用已验证原产品无新增生产代码。"}
```
