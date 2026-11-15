# PLAN029 H1919｜H1918结构门首错：历史H1916 FAIL证据缺source_sha键

- [H1918 governance Action43713116277](https://github.com/lly8666/wbd-next/actions/runs/43713116277) 的角色身份和feature catalog在压缩后均通过；`tools/governance.py validate` 失败，签名结构报告 `evidence is for a different SOURCE`。这是合约与数据结构问题，不是网络产品测试。
- 唯一首错：M0 cursor `last_tested_source=00c41dad927bd5846da79fcec4c42f51d650c645`，H1917新建的详细H1916失败凭据含 `observed_source_sha` 但没带治理强制的 `source_sha`。H1919在**原历史失败证据**仅补同一个 `source_sha` 和真实 `result: FAIL`，不改H1916 Action日志、产品结论、SHA、流量收据或新的H1917验证状态。
- 原始H1917代码SOURCE `fbff58c923dedec097e976820b832114ff673e23` 的真实二系统Action43712621017已经触发；本提交不重派发，也不把Docs SOURCE当作Rust新构件。组件/静态/Windows和Linux库门成功不等于真实4MiB回程、10GiB或全额Stop通过。
