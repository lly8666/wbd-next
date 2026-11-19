# H2206｜Linux原生ARM64 NAT后网卡自动选择、本地密钥输入安全结论

用户新增要求：Linux服务器可仅指定网卡/0.0.0.0（NAT网关后无公网地址）；简化原32字节route-key输入；上一轮通过的WinGUI/驱动控件和本轮功能同步main并保持治理。

上轮H2205的WinGUI与ARM64已合并main [#38](https://github.com/lly8666/wbd-next/pull/38)，追加[#39](https://github.com/lly8666/wbd-next/pull/39)修卡片16KiB/热预算、[#40](https://github.com/lly8666/wbd-next/pull/40)将旧H2202证据从实时校验迁往历史索引；[#40后主线治理Action44353940734](https://github.com/lly8666/wbd-next/actions/runs/44353940734)的Governance和Feature catalog两个Job均SUCCESS，早期44350413489、44350413683、44353080656红灯保留为历史。

当前原生V4 Linux新生产代码H2206 SOURCE `039b88c4eda1edac24d4a9510373f4d127aea74d`：
- `r0/go_overlay/internal/v4productcli/linux.go` 的服务器 `--local-ip` 现在允许省略或 `0.0.0.0`。仅在cold时从 `--raw-interface` 获取**恰好一个**有效IPv4后配置原AF_PACKET raw端点，保持原有目标IP的BPF/用户态匹配、认证/反重放、Go TLS与Rust流；客户端仍拒绝零地址。无有效IPv4、同网卡多IPv4都fail-closed，指明显式`--local-ip`。
- `tools/arm64_linux_netns_smoke.sh` 和 `tools/m0_plan029_linux_crossplatform_coverage.py` 真实两端测试：Normal/tls服务端 `--local-ip 0.0.0.0`，Game2/flows省略IP，两端同源原Go TLS V4扩展v2+Rust原生收发、内核双向TCP/UDP/Stop，验证从网卡v4as解析`198.18.7.2`。x86_64/aarch64 2+2场 PASS_SCOPED，[Action44353147584](https://github.com/lly8666/wbd-next/actions/runs/44353147584)两个job SUCCESS。首轮[44351999455](https://github.com/lly8666/wbd-next/actions/runs/44351999455)独立Go Test外层缺原Rust CGO链接选项FAIL，原二进制build已完成；已修工作流链接环境后真网PASS，历史失败不撤。
- 部署边界：NAT网关需将公网TCP443转发至NIC内网TCP443并开放防火墙，CLIENT指向网关公网IP/FQDN；Linux没有公网IP不影响服务端使用内网NIC。没有测试真实NAT路由器或外部公网，CGNAT无转发仍无法入站。
- 密钥UX：**不**将32随机字节线材降级为8/16可记忆字符，用户自定32位也可能无熵。以8/16位本地别名指向0600文件中原32B随机key，或者另加43字符无损Base64URL显示编码（需要双方另测）才是安全简化；本次没有新增KDF/换格式/旧TLS前导，遵守TLS契约。
- 基础源码hash与实际验收范围分别见[H2206证据](../evidence/M0/PLAN029B-H2206-NAT-RAW-IFACE-LINUX-X86-ARM64-PASS-20261119.json)与[设计/部署](../decisions/M0-PLAN029B-H2206-NAT-IFACE-ROUTEKEY-20261119.md)。实体Win↔ARM、路由器DNAT、网络接口DHCP变化运行中恢复、用户实际驱动安装和PLAN029完整技术验收NOT_RUN。

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"H2206服务端raw-interface网卡唯一IPv4自动选择（省略/0.0.0.0）NAT配置接线、Go负例与Linux原生x86/ARM各两场真TCP/UDP/Stop；不更改route-key随机32B/TLS协议，实网关DNAT未验。"}
```
