# PLAN029 H1864｜H1862仍被已修Rust语法挡在4MiB实测前；本SOURCE只测bulk

- [H1862 Action43617776205](https://github.com/lly8666/wbd-next/actions/runs/43617776205) SOURCE `ad496640` 原Windows/Linux Rust单测在P2前报同一`FragmentKey`构造字面量缺类型的编译错误，故4MiB业务、Tunnel小UDP、产品Stop均**NOT_RUN**。Action终局提交时仍在收尾，不能冒充整场网络判决。
- H1863 SOURCE `b940e538` 仅将该处恢复为`let fragment_key=FragmentKey{`；Windows/Linux native主job eligible Rust tests已经PASS（H1863实网P1仍在途）。`tools/m0_plan029_h1815_p2_real_mixed.py`第4参数`p2bulk`和`perf_counter()`在H1861已修；本提交不再触碰数据面或测试算法。
- 新SOURCE `[plan029-v3-real-p2-bulk]`只触发一场真实签名Windows/Wintun到Linux/WSL2：同VM普通物理socket4MiB后Direct4MiB unpaced，持续小Tunnel UDP的唯一交付/高分辨率p99/最长空洞、两向SHA/半关闭和owned Stop。P1独立H1863 Action单VM A/B并行，不再重复派它。H1864真实业务在此提交时NOT_RUN，029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Separate source-locked genuine 4MiB unpaced P2 after fixing Rust compile and fixture argv; preserve H1862 pre-network FAIL without changing product or feature catalog."}
```
