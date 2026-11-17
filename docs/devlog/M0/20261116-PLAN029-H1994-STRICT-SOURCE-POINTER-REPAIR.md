# PLAN029 H1994｜H1993 治理原FAIL保留，只修被误写的历史证据SOURCE

- H1993 源 `34e87006c51db9c8e183af68482050e6550fb460` 的 [治理Action43840543217](https://github.com/lly8666/wbd-next/actions/runs/43840543217) **failure**：原 Governace `validate_repo` fail-closed，M0 cursor `last_tested_source=ac18e797...` 与已有 `docs/evidence/M0/PLAN029-H1992-H1991-NORMAL-PERF-COMPONENT-AND-REAL-NORMAL-RESULTS-20261116.json` 的 `source_sha=8ed70bc5...` 不一致。旧证据仍真实、原H1993的测试代码并未导致此源锁错误；旧FAIL永久保留。
- 此提交仅修 cursor 的 `last_tested_source` 恢复为真正做过 Win2025/WSL2原 Normal/off 业务的 **8ed70bc54a1aba3ccd460d63089b251280897915**；保留旧 H1992 evidence_refs 原路径原内容和所有样本、没有覆写任何实网结果。将本 H1993 新源的1MiB P2 CPU/p99及Stop全部维持 **NOT_RUN/IN_PROGRESS**，直到收原Action实际回执。
- H1993 [原M0 Action43840543096](https://github.com/lly8666/wbd-next/actions/runs/43840543096) 的 cheap + H1993 七项 128KiB 进度间隔纯Python回归已 success，Rust/Go/双系统仍在途。绝不为纠正治理指针再次派发 [plan029-v3-real-p2-rebuild]；本条提交不含签名场景标记、不改 Rust/Go/测试负载/工作流。
- H1974 的真实 61ms尾延迟与原 4 次TCP重传继续OPEN，普通产品Direct P2性能无因果改善证据，不追极端工况。

```feature-impact
{"kind":"none","ids":[],"reason":"H1994 correct current M0 cursor last_tested_source to old H1991 actual source 8ed70 matching immutable H1992 evidence; preserve H1993 governance FAIL and one in-flight moderate P2 run without redispatch."}
```
