# H2158｜四Game矩阵首次真实首错：FEC变量读取早于初始化

源锁[Action44230873009](https://github.com/lly8666/wbd-next/actions/runs/44230873009)，SOURCE `5b2ace1e0d6fc13d5f0c481bf53e1917d0efb830`：廉价/WinGo/WinRust/LinuxRust及原始Linux服务端构建PASS；四个真实Win2025/WSL2 job启动。Game4off首轮 off 原子进程 `NameError: name 'game_fixed' is not defined`，Game4fixed同样原始 mode 在业务开始前 rc1，整体FAIL保留，不算Game4产品错误或部分PASS。根因是H2153 Fixture在源文件80行校验Fixed标签，但旧变量迟至250行初始化。修复只在 mode 环境读取后定义`game_fixed=mode.endswith('-fec')`并删去后续重复绑定，廉价门严格检查定义早于case引用；并不修改产品Go/Rust/网络策略、owner或原固定FEC行为。新一轮也必须逐case基于真实Windows/WSL2和独立Stop晋级，不能用旧Game4成功回执。

```feature-impact
{"kind":"none","ids":[],"reason":"H2158 repairs only original Python test fixture variable initialization before exact FEC case validation; no product source or network behavior changes."}
```
