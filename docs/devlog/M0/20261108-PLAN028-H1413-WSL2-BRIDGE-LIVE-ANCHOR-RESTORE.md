# PLAN028 H1413｜WSL2 网桥真实数据已通，清理需活 guest 读回

2026-11-08。[H1412 原 Action42492980253](https://github.com/lly8666/wbd-next/actions/runs/42492980253) 已真正发包、真实独立 Linux netns over veth→bridge UDP Echo 和 Windows host vSwitch→WSL2 guest 原 IP UDP Echo 双方向成功；CI FAIL 发生在 teardown。原原始报告明确 `linux_independent_netns_real_L2_UDP=PASS`、`windows_real_vswitch_to_guest_bridge.real_windows_udp=true`，但 `owned_l2_restored=false`，`cleanup_failure=IndexError:list index out of range`；不把欠缺清理复核的 Action 判为整体 PASS，也不说这是产品 VPN 失败（本用例根本没运行 VPN）。

现行脚本在 `finally` 中先终止唯一活跃的 WSL2 UDP guest 进程，再反复调用 `wsl.exe ... ip -j` 做 eth0 原地址恢复，WSL2 on-demand guest 随后可能暂停导致 eth0 IPv4 JSON 列表为空。H1413 最小修改：不改 Windows 网卡/路由、不加任何 VPN 代码或业务探针；先原生 netns/veth/bridge 清理和 eth0 IPV4/default route 精确读回，最后才释放原 WSL2 guest 常驻过程。失败依然保留原报告和工作流 FAIL。新 Action 仅一条原生 underlay 复核；通过之后才构建完整 Windows 1 实例 + 独立 Linux 原客户端共享真实认证 Go TLS443 server 的 L1 网络验收。

```feature-impact
{"kind":"none","ids":[],"reason":"CI-only WSL2 test guest process lifetime / exact underlying network ownership restore correction; no product behavior or protocol change."}
```
