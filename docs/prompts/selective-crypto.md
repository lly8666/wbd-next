# 选择性 TLS 正文加密实验：长期接班提示词

> **2026-10-25恢复核验**：本实验已于2026-10-24按预声明外观否决条件完成，当前 `docs/evidence/selective-crypto-work/status.json` 为 `COMPLETE_SCOPED_NEGATIVE_PERF_BENEFIT_APPEARANCE_REGRESSION`，`open_requests=[]`、`next_action=NONE`。下述文字是**曾授权的研究边界/接班步骤**，不代表仍有待领取开发工单。先核远端状态和[最终报告](../evidence/selective-crypto-work/FINAL_REPORT.md)；无新用户明确授权，不追加原样测试/分类器、不把组件PASS提升为产品资格。

继续 `lly8666/wbd-next` 的 `experiment/selective-tls-crypto` 独立实验。先刷新远端和检查工作区，读 `AGENTS.md`、`PROJECT_CHARTER.md`、`docs/testing/SELECTIVE_TLS_CRYPTO_WORK.md`、它引用的架构/测试计划以及 `docs/evidence/selective-crypto-work/status.json`。核已提交SOURCE、未完成intent和Actions，补遗漏事实后接续，不从旧聊天重建任务，不执行继承的network/fec next_action。

用户要测Normal单lane、FEC OFF下，已经是TLS密文的正文不重复加密能省多少CPU，以及外层TCP-like/TLS-like是否退化。正文只做认证，头部/其他业务仍加密；保持整包完整性、认证、generation、MTU、固定密文重传、无HOL和Stop。按既定单AEAD连续AAD方案，先理想oracle记录成本和重复密文外观反例，不写通用DPI、不为追收益改掉原安全/正确性硬门。

你可在自己的实验分支自主开发必要实验模块、最小配置/FFI接线、Actions夹具与分析器，修复发现的问题并留痕。不改上游岗位状态、不自行合main或部署实机。生产默认不变，实验feature显式启用；方案不是实现收据，已有PASS不自动继承。

所有执行验证在Actions：一性能Action一个场景/测量job，A/A-layout/B同VM顺序，先编译再复用精确hash。ARM64优先，x86代表；主机或产品容量不足就停止更高压力并解释。CPU、内存、实际业务首次交付、p99、队列丢包、oracle成本边界都报告。抓包单独有界运行，包含内层重传导致不同外层位置重复密文的反例；只保留摘要/hash和必要无正文证据，清理owned大文件。

没有明显净收益、或CPU收益伴随外观退化，都可以完成实验并给否定结论。不得刷seed、删失败、宣称不可识别或为了“通过”升级成大规模分类/混淆系统。完成代表覆盖即写最终报告，更新本岗位status和devlog；遇到实现疑点先回读相关既有源码/设计再最小修复。
