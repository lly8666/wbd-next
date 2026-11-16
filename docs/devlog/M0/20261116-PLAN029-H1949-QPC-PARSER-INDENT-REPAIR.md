# PLAN029 H1949｜H1948 首个预执行失败：Python 缩进

- [原 H1948 Action43782225752](https://github.com/lly8666/wbd-next/actions/runs/43782225752) 的 `Cheap workflow and current assembly checks` 在 `python tools/check_workflows.py` 内，`tools/m0_wl_public_normal_e2e.py:2278` 抛出 `IndentationError: unexpected indent`。真实 Windows+WSL2 原生网络步骤因上游 job FAIL 未执行，**不是产品发包/首到失败**。
- 本提交只把 H1948 after-Stop QPC 解析块（5行）对齐已有 H1945 同级 `if`。两腿 Rust TCP、QPC 采样、Python 384 条关联/限制/校验器均不改；禁止因这个夹具失败重发历史 H1945/P1。
- 上轮失败不可改写：H1948 SOURCE `ad35662b` 的原生 P2 状态 `NOT_RUN_CHEAP_SYNTAX_FAIL`；本 SOURCE `NOT_RUN`。一次原 H1948 指定 4MiB + 两策略各384 真 TCP、Tunnel UDP/owned Stop 验收仍应签名执行。保留可能并行的组件编译结果，不将其当产品 PASS。
- 029 整体仍 IN_PROGRESS：首到根因、P1 CPU、D1–D5、Game4、GUI、IPv6、padding和压力退出均 OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1948 cheap workflow encountered Python indentation before any native P2; H1949 fixes exact after-Stop QPC parser indentation with real scenario still pending."}
```
