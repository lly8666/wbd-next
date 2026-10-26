# 同步到正式实验项目分支的记录

日期：2026-10-26。用户明确指定项目统一分支为 `experiment/selective-tls-crypto`，后续应把这个分支作为实验与开发的**主要工作位置**，而不是派生出来的 `experiment/lan-tail-single8-wbd-wiring-design`。

## 实际 Git 状态与同步方法

- 正式项目分支原指向：`ca72b345de5846a5c58f28d6be24b4e2fcd057b1`。
- 最新连续派生的归档分支指向：`6137f4c8e6d2100740a96c5340173214ce2feafc`。
- GitHub 原生 compare 验证：base 为正式项目分支、head 为归档分支时 `status=ahead`，`ahead_by=185`，`behind_by=0`，`merge_base=ca72b345...`。
- 这 185 个提交相对于正式项目分支**仅新增 110 个文件，没有改动或删除任何旧文件**（包括 4 个 `crates/wbd-codec/examples/lan_*` Rust 示例、`tools/lan_*` 实验程序、`.github/workflows/lan-*` 自动化、`docs/evidence/lan-*` 报告）。
- 已通过带 `expected_sha=ca72b345...` 的非强制 `update_ref(force=false)` 执行**快进**，没有覆写或重写正式分支原有 Git 历史。
- 随后只在正式项目分支新增此同步说明，并将总索引与 status.json 的“当前分支”字段指向 `experiment/selective-tls-crypto`。历史实验报告内的原实验分支名保留不改，以确保原始 CI/源码归属可追溯。
- WBD `main` 未改，Rust 正式产品的 Tail8RecordCodec / WBD 主收发整合仍未实施。

## 文件入口

- [实验研发总索引](INDEX.md)
- [讨论、设计变更和已知缺口](DECISIONS_AND_GAPS.md)
- [当前 WBD 低开销接线设计](../lan-tail-single8-wbd-integration/DESIGN.md)
- [单层 TLS 头 + 最后八字节 rolling XOR 的完整性能报告](../lan-tail-one-header-8byte/FINAL_REPORT.md)
- [真实 Linux loopback TCP PCAP 和 Wireshark/TShark 分析](../lan-tail-single8-pcap/FINAL_REPORT.md)
- [完整项目归档清单 JSON](status.json)

## 没有同步到 Git 的资料

原始 PCAP 和 Actions artifact ZIP 仍在 GitHub Actions 的外部归档中：抓包 run 40268297939 / artifact 12627636543，自动 Wireshark 解析 run 40268945000 / artifact 12626843821。Git 中含可重跑的程序及摘要，不应声称外部二进制归档永久入库。聊天逐字记录亦非 Git 归档的一部分。

## 后续使用须知

1. **后续新实验、代码实现、报告/索引更新优先直接落在 `experiment/selective-tls-crypto` 上**，除非明确要求隔离风险的新分支。不要再把设计分支误认作正式项目分支。
2. 以前实验工作流里部分 `on.push.branches` 仍针对当时的历史独立实验分支。这是当初固定实验证据的触发条件，不能仅凭文件已同步就声称 push 到正式项目分支会自动重跑全部历史 CI；有必要时应新增针对正式分支的专门回归工作流。
3. Git 可追溯源码/报告和生产部署、真实两台 LAN 主机测量仍是不同工作阶段。
