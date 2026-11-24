# B69｜系统普通 IPv6 目的 DNS 独立接线（非内层 IPv6 业务）

B68 `10a9fd1fddbe1a0b4e497c80e44b24457fd2c498` 同分支产品CI以实际状态为准。独立默认关闭的 system_dns6 四槽/SAF/冷恢复选项，同时启用B66 IPv4系统DNS。IPv6 UID＋选定netId＋iif lo＋UDP/TCP53 RPDB 19846表、专有wbd_dns6 dummy及局部ULA /128（不对外发布），ip6tables OUTPUT REDIRECT到同一解析器独立[::1] UDP/TCP监听。上游仍原三模式 IPv4 socket，DNS QTYPE与目的IP族独立；支持AAAA查询但没有提供IPv6数据面或NAT64 DNS合成。IPv4与IPv6 journal/family独立，Stop/Restore在撤入口后joined。旧journal默认IPv4、旧profile默认关。实际IPv6 socket→两个真实IPv4 loopback上游测试，IPv6 kernel命令/readback seam；未运行Android实体，IPv6 DNS socket选路、NAT66/SELinux、Private DNS/DoH与完整IPv6数据面仍待验/待接。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B69可选IPv6普通53目的系统DNS RPDB/NAT66/同一IPv4上游解析器及Stop/Restore/配置，内层IPv6业务未接。"}
```
