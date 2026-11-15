# PLAN029 H1901｜修高率SOURCE工作流触发：500/700真实签名环境不可被路径过滤

- H1898 [Action43688298682](https://github.com/lly8666/wbd-next/actions/runs/43688298682) 和 H1899 [Action43688459805](https://github.com/lly8666/wbd-next/actions/runs/43688459805) 首错分别是旧H1894、H1896 Python静态源字符串，只在cheap checks，签名Windows/WSL2及4MiB/512+256+256MiB实际负载**没有运行**；H1900已修复两个assert。
- H1900改动仅`tests/test_m0_plan029_h1896_sustain_tcp.py`/devlog/cursor，但原`.github/workflows/m0-wl-public-normal-full.yml` 的 `on.push.paths` 不包含该测试、H1898新增测试和真实高率fixture；因此H1900仅触发治理、未触发真正的Windows/WSL2签名Action。本SOURCE加三个精确路径：H1896测试、H1898测试与`tools/m0_plan029_h1898_highrate_tcp.py`，不放宽分支选择、签名SOURCE gate、不添加全量默认回归。
- 本次标记明确选定`[plan029-v3-real-p2-bulk]`和`[plan029-v3-real-p2-500-700]`：原Win2025 Wintun/Go/Rust ↔ WSL2 Linux的真实Normal CN 4MiB业务门槛、96B持续Tunnel UDP、512MiB单向500Mb/s目标、单个持久内核TCP全双工各256MiB/总700Mb/s目标、进程/生成器/整机CPU、双侧FIN/owned Stop。实际吞吐按签名report独立报告，低于目标不得伪称达标。此SOURCE不修改任何Go/Rust生产网络逻辑。
- H1897旧治理热读预算超14B，H1898已通过缩短cursor修复且[Governance/Feature Action43688298677](https://github.com/lly8666/wbd-next/actions/runs/43688298677) PASS；本SOURCE继续保持预算、不改阈值。PLAN029 IN_PROGRESS，P1/P2仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H1901 ensures H1896/H1898 test fixtures and signed high-rate script trigger the exact real native source instead of silently skipping it; no product or feature card change."}
```
