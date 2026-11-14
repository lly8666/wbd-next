# PLAN029 H1806｜收同 SOURCE 双 OS Rust 纯组件结果（非实网）

- SOURCE `fa5b38f714c7b8529246e8b8656bb690dfa49c82`, [Action43563550515](https://github.com/lly8666/wbd-next/actions/runs/43563550515) **SUCCESS**：Windows2025 job132352317197 platform 47/47, Rust plan029_ 78/78, private m0_v4_probe plan029_ 80/80、probe V3 ABI 编译成功；Ubuntu24.04 job132352317088 platform 116/116、Rust plan029_ 50/50。两 OS 原始 job logs 均明确含 `plan029_fakeip_multi_a_quota_rollback_preserves_held_and_recovers ... ok`、`plan029_fakeip_failed_multi_a_does_not_erase_prior_uncertain_journal ... ok`。
- H1803 SOURCE301ddd Windows E0609 FAIL、catalog >16KiB FAIL 保留。H1804 E0609 修复虽双 target cross ABI绿，纯组件未因漏记的 TCP53 path 自动触发；H1805 只补测试 path，现完整两 OS 验证。更新 `dns-split-ipv6` 中 H1803–H1805 项为 `BUILD_PASS`，并给独立同 SOURCE 证据；**不把它升级为签名 Windows Wintun D3 物理压力、Complete PLAN029或实网性能 PASS**。
- M0 cursor `last_tested_source` 随本次真实源锁的纯组件改为 H1805 SOURCE，`evidence_refs` 仅本 SOURCE 的 evidence；旧 H1799 源锁签名实网结果转入 context_ref，未丢失。全套 D3-D5、P1/P2 以及 GUI effective 原状态维持 OPEN/NOT_RUN；本次只收已在途 Action，不 dispatch 新实网场景。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Promote only H1805 same-SOURCE Rust FakeIP multi-A quota pure component tests to BUILD_PASS on actual Windows/Linux; retain physical D3-D5/P1-P2 NOT_RUN."}
```
