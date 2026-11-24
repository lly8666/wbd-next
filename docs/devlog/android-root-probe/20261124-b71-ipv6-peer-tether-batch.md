# B71｜IPv6真实冷网关Echo＋现有热点IPv6下游＋批量FIB

B70 `1a895938937434e0779daa6d153642f5c5f30cba` [#45324322599](https://github.com/lly8666/wbd-next/actions/runs/45324322599) 截至本批开始B69 DNS/规则与B70双端owned Host及治理PASS，整构建待实际结果。

客户端显式IPv6 carrier启用后，实际本地SIT/FIB读回不再等于peer ready：独立精确root source6/dest6/uid0路由，Go Bionic raw ICMPv6 socket绑定wbd_sit0，随机nonce，最多2次/2s每次，无后台线程，必须实际原M4双向Echo Reply后才给peer ready回执；旧服务端/错误TUN地址明确失败，不新TLS wire或伪造ACK。容器unshare隔离lo真实raw ip6:58 Echo试验通过（非SIT或Android E2E）。

B65实际软件下游与ifindex已验且B70启用时读取真实现存global IPv6 /64（每prefix一实际源地址，至多4个），原IPv6私有FIB 19847精确iif/from/to、下游↔SIT conntrack FORWARD、SNAT66到原IPv4派生IPv6 lease；无额外RA/DHCP/translator线程，不改全局转发设置。无实际IPv6 prefix保持原IPv4热点。prefix renumber需冷重连，硬件/BPF仍要求已有软件模式。IPv6 carrier本地MTU/6rd readback与恢复区分，部分启动或TUN消失后可撤精确alias/tuple。全UID冷路由批量ip -4/-6 -batch，恢复按反向批量和原journal确读，不改变任何IPv4/IPv6普通数据热路径。Host command seam检查两prefix、UID范围、精确peer scope与batch/Restore，真实Android+Linux IPv6公网及热点设备未验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B71真实IPv6冷网关Echo、已有软件热点IPv6前缀SIT/SNAT66、全UID批量冷FIB和恢复；非实体E2E。"}
```
