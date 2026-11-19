# H2160｜保留B4真实TCP硬门，校正旧静态文字断言

[H2159 Action44235378758](https://github.com/lly8666/wbd-next/actions/runs/44235378758) **FAIL_CHEAP_PRE_NATIVE**：原B4静态测试 `tests/test_m0_plan029b_b4_scope.py` 要求`if p029_direct or p029b_b4:` 的旧源文字；现该支路为 `if p029_direct or p029b_b4 or p029b_game_case:`，B4未删，只拓展到新Game源锁验证。更新该断言并保持B4真实Winsock/TUN TCP/Stop硬门；Game矩阵仍真实Windows→Linux TCP双内核回显，旧028 Linux主动入站方向明确NOT_RUN；原Normal/028双向入口不改。

只有当前SOURCE的四Game真实20 policy原生+双方Stop和所有cheap、WinGo/Rust检查才算完成。此提交不含生产Go/Rust/FEC/wire改动。

```feature-impact
{"kind":"none","ids":[],"reason":"H2160 updates only historic B4 static source guard after scoped Game matrix true-kernel TCP test selection; runtime/ABI/policy unchanged."}
```
