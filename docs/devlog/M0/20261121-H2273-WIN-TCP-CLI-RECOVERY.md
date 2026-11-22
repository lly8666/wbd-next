# H2273 · Windows 1%/5% TCP 测试入口的实际失败与修复（2026-11-21）

H2271 SOURCE `bb32770f65948bae629481b30259c1277a3233e2` 的 signed Windows2025 Wintun/Npcap ↔ Linux WSL2 Go TLS/Rust 真实双端 Actions [loss1 44921318653](https://github.com/lly8666/wbd-next/actions/runs/44921318653) 和 [loss5 44921321136](https://github.com/lly8666/wbd-next/actions/runs/44921321136) 都完成 **Action FAIL**。真实 Go/Rust/Windows DLL/Linux server构建、Windows真驱动安装与 WSL guest 原生启动均 PASS 到运行原两端业务阶段；新 H2271 TCP 服务端进程无监听回执，报告 `H2271_REAL_KERNEL_TCP_LISTENER_NOT_READY`，原生 Stop 清理完成。检查新增 Python 脚本源码，发现虽定义了 server/client 函数，**遗漏 `if __name__=="__main__"` 的CLI分派**：Windows/WSL 子进程直接退出且日志为空，是可直接重现的测试应用 bug，不能记为 WBD 1%/5% TCP product FAIL。源 bb327 的原失败绝不改写。

同一 Windows 原工作流真实 test-owned 防火墙只允许 Wintun 10.66.0.2 的 TCP **45902**、来源 Linux TUN 10.66.0.1，H2271 自选 46973 会使反向 Linux→Windows 额外被阻断。本次复用已经创建、读回并由既有 owned Stop 删除的精确45902端口，不扩大任何平台防火墙规则、不改产品配置。新增真实CLI入口、廉价静态CLI自检到现有 dispatcher；Windows 和Linux两个客户端仍由同一原 Go TLS/Rust owner与 netem 驱动四个内核TCP bulk＋160小TCP真实回显（先旧UDP后新TCP），所有双端Stop保留。

这次仅改 H2271 诊断脚本、自动预检与本 devlog；不碰产品源码、组装、网络默认或TLS安全。首次两个旧FAIL保留，新的 exact SHA 双场验证至收到 Actions 结果前仍 NOT_RUN。诊断结果应按两端 OS 的真实goodput、P99、未回与 native TCP/UDP source区分；如果新子测真实失败再按实际日志单一定位。

```feature-impact
{"kind":"none","reason":"H2273 fixes test-only missing Python CLI main dispatch and uses existing owned Windows TCP45902 firewall test port for real Wintun/WSL2 data path; no production code, defaults, configs, security or owned Stop change."}
```
