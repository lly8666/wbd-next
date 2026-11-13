# PLAN029 H1762｜H1761真实签名 TCP echo 首错：精确 WSL2 46112 收件口

- [H1761 Action43452721588](https://github.com/lly8666/wbd-next/actions/runs/43452721588) [原始产物](https://github.com/lly8666/wbd-next/actions/runs/43452721588/artifacts/14053607260)：单代原始 Go TLS/Rust、Wintun+Npcap、OS Applied/Ready、精确 Defender PREPARE+ENABLE、Tunnel UDP、CN DNS CNAME FakeIP Direct UDP物理Windows↔Linux均 **PASS**。新的真实Windows应用 FakeIP TCP `connect` 成功，发送32KiB半关闭后 `recv` 20秒超时；物理Linux TCP收件证明在旧归档 allowlist 缺失，不能断言Rust中继错误，也不能宣布D1/D2成功。
- 现有独立 WSL HyperV Allow只为原始FakeTCP建立 `LocalPorts=443,444,445,446` 且 `RemotePorts=41031..41034`。新 TCP 46112 及 Windows动态源端口不可能与之匹配；而UDP46111已在同源成功。这是首个最小可证伪环境假设。**不修改老规则**：另建单个 `WBD-M0-WL-<run>-P029-TCP46112`，精确当前WSL guest IPv4、Windows物理源、TCP46112、当前WSL creator，创建后按同属性读回；`always()`按接收凭证和owner清理，严禁清理外来项/全局放行。未观察实际 46112 TCP packet之前仍为假设。
- H1762扩展同一SOURCE Normal原生夹具：双方实际TCP connect/accept/FIN点位加日志，并纳入 `tools/m0_wl_mode_evidence.py` 的红acted allowlist；不会为PASS只上传伪回执。将029普通非CN Tunnel TCP比较器限定为Windows app→Linux TUN真实TCP回显/FIN；旧028 Linux→Windows反向比较器保留在非029分支和历史FAIL，不虚称它通过。
- 另补H1761证据的规范 `source_sha`，新H1762以失败 SOURCE `c5a0c610`单独保留。
- H1762目录卡体积超16KiB引发Feature Catalog拒绝：规范化为不丢失历史source和证据的紧凑JSON；此提交仅重新声明卡片影响，不更改产品网络或CI实测结论。仅一次新 SOURCE自动带 `[plan029-v3-real-direct-udp]` 运行签名Windows/WSL2；不派发同场景重跑。完整029 D1–D5/P1–P2、GUI/padding/性能仍开放，030不开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1761 genuine Direct TCP 32KiB recv timeout after UDP PASS; H1762 scoped physical HyperV TCP46112 hypothesis and real evidence capture"}
```
