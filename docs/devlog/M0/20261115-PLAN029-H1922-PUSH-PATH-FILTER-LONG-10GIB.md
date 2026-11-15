# PLAN029 H1922｜长10GiB Action必须走原生push路径过滤器
- H1921 `7464ff95cfb3c450ca6cc83836df2b00b9ef9d3a` 仅更新docs/feature/cursor，尽管commit message带有long marker，仓库`.github/workflows/m0-wl-public-normal-full.yml` 的GitHub `on.push.paths`**没有覆盖这几个文件**，所以只有 [governance Action43716113039](https://github.com/lly8666/wbd-next/actions/runs/43716113039) SUCCESS；该SOURCE的10GiB **未启动**，不是假红/真红，更不能算H1921长P2 PASS。
- H1922在已经允许触发原生工作流的 `tests/test_m0_plan029_h1898_highrate.py` 补真实回归：检查三项长场景标记都被源工作流识别、test文件在push.paths中、`4MiB` Direct app完整证明在`run_highrate`前完成、source严格取`GITHUB_SHA`且同机物理→Direct CPU增量计算保留。只触发**一轮**本SOURCE原 Windows/WSL2 Real P2，不改Rust/Go生产字节、不重派历史未运行场景。
- 新源提交明确`[plan029-v3-real-p2-bulk]`、`[plan029-v3-real-p2-500-700]`、`[plan029-v3-real-p2-long-ab]`同时启用，以先4MiB功能再同VM物理/Direct两路径10GiB保证正确性、Tunnel96B UDP跨度、过程user/kernel CPU/实际GiB、RSS/Stop。已通过的H1920 4MiB PASS仍是**历史不同SOURCE**证据，H1922本次要重新锁源；长CPU不是新旧代码同VM A/B。
- D1–D5/P1–P2其余、GUI/Game4/IPv6/padding和CPU/小流延迟优化继续OPEN，028限域不重开，030不启动。
