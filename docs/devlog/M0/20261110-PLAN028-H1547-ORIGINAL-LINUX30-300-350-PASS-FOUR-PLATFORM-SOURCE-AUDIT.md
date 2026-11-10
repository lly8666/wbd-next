# PLAN028 H1547｜最新源码四平台重新核验：Linux 高压两档真正通过，Windows 五客户端仍需产品修复

时间：2026-11-10；**main** `e6485a0db134ff5e653d048eb1f8c341a412eccb`；经过原生运行的 Go 产品 SOURCE `ed965f2dd93bc5520d9a17f211ff39029d4d6594`（当前 main 仅领先一笔文档/治理变更，不改 Go/Rust 源）。依据：下载并逐字段审计 [H1541 原始实测 Action42825317650](https://github.com/lly8666/wbd-next/actions/runs/42825317650) artifact13768194541，核验源锁 Go 两可执行文件／Rust .so SHA256、内核10秒双向账、5客户端原始 UDP/TCP、认证 M4、6 Stop、原始告警。

### x86 Linux 原生 300–350 Mbps 验收结果

- **loss30 PASS_SCOPED**：真实200ms/方向且物理30% netem、600s、单TLS443五独立账户 Normal/Auto/Game2/Game4/Fixed6，核验稳定外层双向合计 **304.271 Mbps**，**40/42** 稳定十秒采样达标，最大活跃收件间隙各方向200ms、六个独立 owned Stop 全部证实，host monitor、native fixture、outer monitor都原退出码0。
- Carol Game2 整组服务端原 M4 **6个**认证代，旧代 Stop 成对；Dave Game4 **5次**客户端热换均有服务端原M4对应；Alice/Bob/Erin Normal 服务端 B 阶段确认 **6/5/4 共15次**全部为真实认证 Health 提交。原始旧 H1274 oracle 的 Normal `ROTATION_CONTINUITY_NOT_PROVEN` 及在持续30%物理损伤下把 recovery 强制95%的原警告**保留在原 ZIP**；新独立资格判定使用真实服务端 B_PENDING→已认证 Health→B_CLIENT_READY 端口，明确 `hard_faults=[]`，有根据地判业务 **PASS_SCOPED**。
- **loss0 源9b260**上次原生 **333.930 Mbps PASS_SCOPED**，不是此次Go ed965重跑；用户已接受此前测试，不制造这笔新源的loss0通过。
- 之前 H1540 原旧混组 FAIL 及 H1541 首次 shell127/误端口边界单测 FAIL 均保留历史记录，不能追写原 Action 为 success。

### 最近几天的默认构建缺口复核

| 原生链 | 当前源真实证明 | 未证明/仍阻断 |
| --- | --- | --- |
| Linux x86 | 11文件 H1285 正确 FakeTCP source-locked、Game2 本代真实 TCP 5tuple整组、防旧候选；两个原Go二进制新编 ed965、Rust SHA一致；600s loss30 PASS | 0% 最新Go SOURCE未重复压测，物理跨机器 NOT_RUN |
| Linux ARM64 | [Action42825317709](https://github.com/lly8666/wbd-next/actions/runs/42825317709) 真 ARM64 runner 当前 `ed965` 原Go client/server + Rust/ISA-L ELF183/SHA256 **PASS_BUILD_ONLY**；Go全文件、11 FakeTCP 默认装配、Rust Game Lane 22/FEC2 7项单测通过；非旧140a冻源伪合格 | 当前ARM64五客户真实网络、600s/Stop **NOT_RUN** |
| Windows x86_64 | [Action42825317732](https://github.com/lly8666/wbd-next/actions/runs/42825317732) 现役 canonical 112源码操作＋受控23 Windows extra＋CLI Test，全部94现有Windows overlay覆盖，Windows Go/Rust编译与原生二/五账户具名OS event单测通过，常规单Windows/WSL2 Linux七模式实际内核双向UDP/TCP及Stop **PASS_SCOPED** | 五个独立 Wintun **同机同时运行**继续 `route is not owned`／WFP独占阻断，五设备Ready0，不能称作实际多客户PASS |

- **Rust跨源再核验**：REST compare `9b260553...ed965f2d` 共24个提交、49个变化文件，但 `crates/*`、`*.rs` 与 Cargo 文件 **0** 项变化；H1541只复用了 SHA256相同的Rust原库，近期Go最新代码已真正重编。标准 x86/ARM64及Windows相关当前源Rust构建单测同时PASS。
- 没有发现上述默认装配范围内**新的漏装已修复源码**。但“编译通过”不能等同五Windows多Wintun资格或ARM64 600s性能通过；Windows机器级共享 /32,/1/WFP与用户lease必须明确设计所有权，不能冒领第三方route，不能强行默认开启。
- Feature card新加H1541实质PASS，保留H1540 FAIL历史条；减小旧验证项重复平台名称以满足目录16KiB限制。游标 evidence_refs保留少量权威当前证据，满足max8；PLAN028 `IN_PROGRESS`。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Record verified source-current H1541 five-client high-loss original Linux PASS and refreshed source-locked default x86/ARM64/Windows platform wiring coverage; preserve historical FAIL, Win five-route/WFP fail-closed and network qualification gaps."}
```
