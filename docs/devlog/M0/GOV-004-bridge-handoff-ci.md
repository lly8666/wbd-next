# GOV-004 桥接契约、接续记录与治理 CI 分层

用户授权完成上一轮审查的四项收口，并提供全新 M0 的固定开工提示词。基线 main `33c0794`；独立维护分支 `governance/bridge-handoff-ci-20261015`。不改产品 Rust/Go 源码、worker 分支/权限/epoch，不把本次治理验证当产品资格。

## 已做

- 01-CONTROL-BRIDGE 与 HOT_PATH 统一 Prepare→受保护回复→DetachTransition→CommitAdmission→双 owner 确认→Active。记录 early 移交、精确 TX/RX 边界、半安装失败、Detach 后 Commit 失败、旧 lane 继续与真实 lease 释放；修正早期激活后才 Detach 的矛盾，不宣布已有完整实现。
- 11-IMPLEMENTATION-GATES 给既有 M0 023 排出真实认证、Normal/off 首到/关闭、Linux 真实 I/O、普通性能基线四步；测试复用生产函数，仅在设备/时钟边界注入，不继续搭第二条 test-only 数据路径。
- project 简化为阶段/入口，registry 保留分配和职责；去除方案“未开始/reserved/只有治理工作流”过期状态及 M1 提示词相反的任务权威描述。当前 M0 cursor 在完成维护并核精确证据后以独立 H 整理；不在实质提交中覆盖它。
- 普通 push Governance 保留身份/权限/来源/结构/引用核验，完整工具 drills/model 归 maintenance 或显式手动 selftest。checks/receipt 清楚区分 NOT_RUN 和 PASS，缺核心步骤或手动自测缺失必须 FAIL。进度/请求/证据数据不再触发重复 maintenance；规则、工具、工作流、policy、必跑清单、检查点等变化仍跑全回归。

## 验证与边界

只在 Actions 执行验证。本地仅编辑、读取代码和 Git 差异检查。新增反例覆盖 mandatory skip/fail/cancel、手动 selftest 少跑、伪造 PASS、未知事件/观察、维护触发范围；通过前不称完成。固定 SOURCE、run/attempt、artifact 及实际数量待结果另附 evidence。所有旧失败、旧 CPU INVALID、产品/物理/500Mbps NOT_RUN 保留。

合入前核 main 是否前进；保留其他 agent 最新任务事实，不 force push、不改 worker cursor。治理维护收口后，新 M0 直接按远端 registry 的 023 继续实际链路，固定提示词见 `docs/prompts/M0.md`。不再顺带扩大治理框架。

## M0 接续：合并与 SOURCE-exact 产物结论

2026-10-15 M0 根据用户转述的未完交接，核实 PR [#5](https://github.com/lly8666/wbd-next/pull/5) HEAD `318fba67e155e901b49d55122e1d84bc80cabdf8` 仅 1 笔候选提交、20 路径，无任何生产 Go/Rust crate 或 worker 权限/epoch 修改。候选 [Actions 38742200019](https://github.com/lly8666/wbd-next/actions/runs/38742200019) 169/169 Python 回归 SUCCESS，artifact `11975009448` ZIP SHA256 `6d8b159380e7f5b5ec83f58e82c7a710998402701e6f4ed054ac82117aad469c` 已独立核 metadata 和日志。原 main `33c0794b` 不变，PR merge commit `e2c2657edd74a45d87f5074a65d1b715b6705a65` 成功，PR closed/merged。

**合并后不能借用候选绿灯：** 同 SOURCE `e2c2657edd74a45d87f5074a65d1b715b6705a65` 的 [maintenance 38743199711](https://github.com/lly8666/wbd-next/actions/runs/38743199711) 169/169 PASS、artifact `11976483518` digest `51a745efa98dd2e7599677350022627ca4710696523a904479ba7e871d4fa1a3`；[Governance 38743199809](https://github.com/lly8666/wbd-next/actions/runs/38743199809) PASS，但 push scope **only identity/structure**，自测/model 明确 `NOT_RUN`，artifact `11976239464`；[G2 38743199565](https://github.com/lly8666/wbd-next/actions/runs/38743199565) build+consume SUCCESS，产物 `11976740797` / `11976970735`；workflow_run 作用域跳过 main 的 `38743244903` 为预期。精确 run/job/ZIP digests 在 `docs/evidence/M0/GOV-004-bridge-handoff-ci-main.json`。没有产品/真实业务/物理/性能新验证。

下一步只更新 M0 cursor 的独立 H，比较 S→H 改动清单必须**仅** `.governance/workstreams/M0/cursor.json`。以 H **确切 SHA** 查询 push Actions：Governance scope identity/structure PASS，完整维护回归应无 run；若意外触发，记录事实而非假称优化成功。此 PR 只完成架构/CI 收口，不满足 M0 owner023 产品 done_when。
