# PLAN028 H1395–H1396｜真实原始 L3 资格、两旧黑洞离线账与 Windows ISA-L 构建

2026-11-08 main `1a47fa5a` 接续。H1392 [原始 Action 42475419721](https://github.com/lly8666/wbd-next/actions/runs/42475419721) 已完整结束，两条 native ARM64 1800s 五真实 GoTLS443/Rust M4 客户端原始 ZIP **各36文件 CRC PASS**、Game4 原 Rust ISA-L native quanta 非零、安装/结束前真实双方临时 veth 邻居 10/10 永久。baseline 0 alert、最大实际活跃发送无收件 50ms；heterogeneous Erin 30.0034% UL / 30.0223% DL DATA netem，0 alert，最大120ms；全部五客户端 authenticated rotation/Stop PASS_SCOPED。完整原 hash/有效 scope 见 `docs/evidence/M0/PLAN028-H1392-SOURCE4444-ARM64-L3-ARP-ISAL-TWO1800-PASS-SCOPED-20261108.json`。原 H1389 3.31/3.32s 真性能 FAIL **不抹掉、也不声称 ARP 唯一根因**，两次运行同时改变了 L2 与 native ISA-L 编译资格。

[Windows H1394 original source 1a47 Action 42476806685](https://github.com/lly8666/wbd-next/actions/runs/42476806685) 初次失败在 signed Npcap/Wintun 业务之前：Windows runner `C:\\Program Files\\Microsoft Visual Studio\\2022\\Enterprise\\VC\\Auxiliary\\Build\\vcvars64.bat` 不存在，`nmake` 不识别。Linux 原 Rust build/构建预检成功，但 Win DLL 和任何 Win 真业务 **NOT_RUN**。H1396仅修 Windows native 构建阶：用本机 VS Installer 的 vswhere 定位含 x64 VC tools 的实际 Visual Studio edition/version，执行同一个 `vcvars64.bat` + `where nmake` + 官方源 `nmake /f Makefile.nmake`；源签名/ISA-L pin、原 Go TLS/真实驱动/WAL/Stop 硬门不变。不因 CI 编译失败拒认以前 H1388 Windows MTU 真实 PASS。H1394 原 CI FAIL 留档。

2026-11-08 与 L3 夹具改动同推送自动触发的原 H1353 x86 Action 42475183161/H1368 ARM64 Action 42475183088 已执行 180s 原始真实网络；其旧审计在 `len(tx)==len(rx)==18000` 处断言失败。原 `traffic.py` 实际每方向桶数 **19001**（180s active + 10s drain + 最末桶）。H1395 只修审计长度为19001，仍以原 0–180s 时间窗检查每个发送/接收、不改变业务损失/时间预算；新 workflow **只下载原 2 ZIP 做离线分析**。H1368 原 zip 缺少黑洞物理事件 `h1353-physical-game4-blackhole.json`，即使 original console 输出了恢复，严禁捏造完整事件 PASS，应标 NOT_QUALIFIED。关闭上述两个旧 workflows 的自动 push 路径，只保留 workflow_dispatch，以免为报表修复重做 180s 原始网络。原始 Action 失败保留。二者离线结论必须来自 H1395 原产物。

Windows 仍执行用户目标：一台 Windows 一个 VPN 客户端；服务端多端共享需要后续一台 Windows + **独立 Linux 客户端**，不以同机第二 Windows Wintun 权限绕过替代。PLAN028 **IN_PROGRESS**，后续不先行授权029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Windows native ISA-L runner MSVC discovery; blackhole analysis-only cardinality and offline evidence; original user-facing product protocol unchanged."}
```
