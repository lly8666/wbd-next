# PLAN029 H1801｜治理门禁真实首错修正（非产品回归）

- H1800 [Action 43561934666](https://github.com/lly8666/wbd-next/actions/runs/43561934666) 自动 governance **FAIL**。Feature Catalog job 首个明确错误：`startup-flow-padding: unknown verification status`；工具 `tools/feature_catalog.py` 的固定枚举只接收 `FUNCTIONAL_PASS` 等，不接收泛化 `PASS`。Governance structure 同批失败，role/identity 成功；未运行新的物理网络场景，不可记为真实业务 FAIL。
- 本批只把功能卡 H1797 default-off 和 H1799 flows 两项限定 native 测量的 `PASS` 改为 `FUNCTIONAL_PASS`，补齐 H1797 对应已完成 SOURCE `30f234900f0d83007df975dfa071339ab4b9a7fe`；H1799 SOURCE 仍为 `6a77d23d54847aacc8ef99bba1104cf1758ca02d`。二者实测范围原样限定，完整 029 仍开放。
- 此处 `FUNCTIONAL_PASS` 只指卡片 `scope` 中已完成的 Windows/WSL2 产品现场 TCP/UDP/Stop/H1799 NPF，不代表 GUI effective/D3-D5/P1-P2 或全面性能合格。只触发 push 自有治理，不重复 dispatch 已通过 H1799。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"Correct fixed feature catalog enum on already-evidenced scoped signed H1797/H1799 results; do not expand qualified scope."}
```
