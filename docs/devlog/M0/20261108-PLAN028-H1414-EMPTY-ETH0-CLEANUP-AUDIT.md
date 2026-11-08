# PLAN028 H1414｜还原前 eth0 无 IPv4 不是缺网卡

[H1413 原 Action42493317201](https://github.com/lly8666/wbd-next/actions/runs/42493317201)：实际 Windows host vSwitch→WSL2 bridge UDP、Linux 独立 netns veth→相同 bridge UDP 两条真实内核往返仍 PASS。第一次假说是只有唯一常驻 guest 被杀导致 eth0 不可见；修了顺序后仍发生同一报表错误，说明该假说并未获证。真实静态程序调用链是：桥 setup 将原 IP 从 `eth0` 转到桥，`finally` 先拆桥 / eth0 nomaster，再运行 `witness()`，后者直接索引 `ip -4 -j addr show dev eth0` 第一项。对*仍存在但尚未恢复 IPv4* 的合法接口，iproute2 返回 `[]`，所以 IndexError/自造 RuntimeError 在 `ip addr add orig` 前终止。

本次只在恢复中先用真实 `ip -j link show dev eth0` 验证物理设备存在（必须1条），再允许 `ip -4 -j addr` 没有地址，按原源IP/掩码恢复；之后独立读回原 IP/网关/桥/namespace 资源全归位。仍是 test-only underlay，任何真实 Windows VPN、Linux VPN、TLS、Stop 全部 NOT_RUN，不把已通过网络探针当产品资格。原 H1412/H1413 CI FAIL 保留，一次短 native复核是为了保证高优先级 owned 资源恢复，而非刷网络种子。

```feature-impact
{"kind":"none","ids":[],"reason":"CI underlay cleanup exact Linux iproute2 no-address intermediate handling; no product behavior, hot code or config change."}
```
