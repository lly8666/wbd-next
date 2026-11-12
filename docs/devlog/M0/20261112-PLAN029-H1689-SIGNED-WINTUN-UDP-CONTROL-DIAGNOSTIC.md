# PLAN029 H1689｜签名 Windows 原 TCP 门的单次对照诊断（不修改 WFP/防火墙）

H1669/H1672 的真实 Windows Wintun SYN→kernel SYNACK 两次无匹配回包，且本机 TCP listener self-connect/accept 已 PASS；原错误不复写为成功，不能据此选择 Direct-only smoltcp。当前追加**一项不同的、有界诊断**，同一已验证签名 Wintun/IP Helper /32/route/real listener 环境，先做 Windows 原生 UDP listener self-probe，再注入带有效 IPv4 头、UDP checksum=0（IPv4 允许）的单个 UDP datagram，读取本机 listener 是否收到；随后沿原测试收 TCP SYNACK。UDP 成功仅区分通用 TUN 入站 vs TCP 接收边界，绝非 Direct UDP 出口 PASS。

H1672 PowerShell firewall read-only 查询返回 exit1，单次用 `netsh advfirewall show allprofiles` 补只读上下文，**不动 Defender、第三方防火墙、WFP guard，不创建 allow 规则**。失败情况下两个原门仍 FAIL。Action 由既有 `m0-plan029-h1669-native-direct-tcp-feasibility.yml` 对本测试文件的 push-path 自动触发一次；不人工多次重派，不刷 seed。真实回执未收集之前 H1689 状态为 **IN_FLIGHT / NOT_QUALIFIED**，H1688 GUI 配置状态独立。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"One real signed Wintun kernel UDP ingress control to narrow H1672 TCP SYNACK absence without WFP or firewall changes; does not promote Direct/Tunnel product."}
```
