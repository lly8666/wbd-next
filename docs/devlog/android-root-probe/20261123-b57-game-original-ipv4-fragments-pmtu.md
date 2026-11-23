# B57｜Android原Game2/4 IPv4 MTU：大UDP DF0真实分片、DF1本地PMTU

起点 `fff507152d51fb604eed3d6109e3a97debafa3c2`，[Dual64 #45196398008](https://github.com/lly8666/wbd-next/actions/runs/45196398008) 11 SUCCESS/4 SKIPPED（原Go/Rust双ABI、签名arm64-v8a APK、两个Linux原Oracle及6个Host）。Android实体 Game2/4 应用TCP/UDP/DNS/CPU依旧 NOT_RUN，不用软件绿灯冒充。

此前原Game的 `AndroidOwnedTun::read_ip` 已完整读取最多65535B，却在 `n>inner_mtu` 立即丢弃，日常较大的普通 App UDP 与 IPv4 PMTU 没有可见反馈。本批一次补三个实际业务面：

- **DF=0 IPv4**：同一真实TUN读者沿原`admitted_client_source`及DNS路由，经现有B16 `v4_android_ipv4_mtu::fragment` 产生RFC791保留IP ID/offset/MF、copy-bit options的IPv4片；每片仍调用 **原`GameAdapter.offer/drain`→同lane M3/AEAD/PN→真实RAW**。仅在超单源预算时使用一个2KiB scratch；完整IPv4 65KiB在最小普通576 MTU最多119片，同次最多128片并在原Stop请求时停止，没有新线程、TUN reader或IP/TCP协议栈。
- **DF=1 IPv4**：原B16 `fragmentation_needed` 生成 ICMPv4 3/4，通过原Bionic `AndroidOwnedTun.write_local_pmtu_icmp_ipv4` 写回原App的同一代TUN，告知实际本次Game inner MTU；不向远端发送假M3确认。正常≤inner_mtu包仍是原快速路径，原MTU/Go/协议配置无变动。
- **物理UDP53大查询**：放开过早MTU拒绝后，若现有`DnsRoute::PhysicalUDP`已认可请求，继续原同一绑定真实PhysicalNetwork socket，不把该请求假送M3；其它业务与隧道DNS继续同原路径。
- 三条B57 Host用例运行完整4KiB真实IPv4分片及重组/校验、65KiB原UDP最小普通MTU及原DF1 ICMP/错误中断；已加入现有Rust Host脚本，正式APK源码门同源核验。没有额外Workflow或旧探针重复dispatch。

本批并未补Android物理TCP53本地TCP流、系统netd DNS、IPv6、热点或默认路由；Android实机设备和性能 NOT_RUN。用户未单独授权手机/服务器；main与M0不写。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B57原Game2/4完整TUN IPv4大包不再直接丢：DF0复用现有B16 RFC791片经原GameAdapter/M3/RAW，DF1用现有原TUN ICMP3/4反馈，较大物理UDP53继续原socket；新增3条Host测试，无新worker或协议栈。"}
```
