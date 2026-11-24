# B73/B74｜统一可配置隧道DNS及IPv6热点DNS

B72 SOURCE `4e98b7bc8c250c7f8531c591840f9e533b7d369f` [产品 #45328655906](https://github.com/lly8666/wbd-next/actions/runs/45328655906) 11 SUCCESS/4 SKIPPED；[功能卡 #45328655868](https://github.com/lly8666/wbd-next/actions/runs/45328655868) 超16KiB FAIL。完整历史52条verification原样归档，本卡缩减活动记录，不改写旧结果。

B73：隧道DNS默认1.1.1.1，可选数值IPv4，同一设置从Root Activity/四槽/SAF/冷恢复到Go参数及原Rust Normal/Fixed/Auto单generation UDP映射、Game2/4组UDP映射；RX按当前上游逆映射，不额外逐包FFI、线程或DNS引擎。CN非CN分支、App TCP53、系统IPv4/IPv6普通DNS及热点同一Go DNS resolver和真实TUN-bound上游路由，物理DNS仍独立。

B74：已有软件热点IPv6 /64及B70/B71 IPv6 carrier启用时，在实际下游地址各开内核UDP/TCP DNS listener，原IPv6 journal精确下游PREROUTING DNAT/INPUT及Stop撤销，复用B64/B66/B68 resolver、B73上游与三DNS模式；普通IPv6 DATA仍原kernel SIT/6rd，无新增逐包转发线程。无RA/DHCP/Private DNS设置改动。新Host正常场景与源锁双ABI/签名APK/原Linux Oracle待CI，真实设备及性能NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B73各原生模式可配置隧道DNS及B74 IPv6热点DNS与原配置/Stop接线；归档B72历史功能卡以恢复目录大小资格"}
```
