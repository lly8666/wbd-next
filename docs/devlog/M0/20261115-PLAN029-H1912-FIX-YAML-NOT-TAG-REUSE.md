# PLAN029 H1912｜GitHub Actions 复用任务的 YAML 条件首错

- [H1911 Action43704387233](https://github.com/lly8666/wbd-next/actions/runs/43704387233) 立即 FAILED 且**jobs=[]**；Github YAML plain scalar 的`if: !contains(...)`行首被解释为非法`!tag`，根本未进入Go/Rust或Windows/WSL2业务。
- 对这三个本要在复用场景跳过的并行编译job，只加外围括号`if: (!contains(...)) && ...`，原表达式真假与排他条件完全相同；Linux original build 的中间`&& !contains`原本合法，H1909 EXE/DLL和Linux artifact SHA及source-locked`gh api`+manifest+产品Git-diff空验证均不变。新增Python静态契约阻止再次输出行首`!contains`。
- H1911失败保留；H1912需要GitHub成功解析工作流、跳过已合格WinGo/WinRust/LinuxRust和原Linux二进制重建，并在同一签名Windows2025 VM复测2GiB单向/全双工1.5GiB两方向+Tunnel96B UDP+双owned Stop；**H1912真业务NOT_RUN**，不声称重复CPU/GiB已有结论。

```feature-impact
{"kind":"none","ids":[],"reason":"H1912 only corrects YAML scalar syntax of three compile-skip conditions for exact H1909 binary reuse and adds static guard; no product change."}
```
