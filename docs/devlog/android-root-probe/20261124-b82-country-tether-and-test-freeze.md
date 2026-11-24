# B82｜普通CN IPv4热点接线与集中测试准备

基线 B81 `dd6d05f99e3b38e3523bb801303a66233b2adaad`，仅 experiment/android-temp-root-probe / Draft PR #36。B81 [产品 CI](https://github.com/lly8666/wbd-next/actions/runs/45362429746) 9 SUCCESS / 1 FAIL / 5 SKIPPED；[CN Job](https://github.com/lly8666/wbd-next/actions/runs/45362429746/job/138335568679) 官方 8472 typed rules 实际 Go/Rust PASS，双ABI及两Linux Oracle PASS；APK历史 send_staged 断言 FAIL。维护 [#45362429783](https://github.com/lly8666/wbd-next/actions/runs/45362429783) 831 tests OK，随后旧 engine 依赖图未包含 main regex-lite FAIL；功能目录 [#45362429674](https://github.com/lly8666/wbd-next/actions/runs/45362429674) SUCCESS。

- B82 将已合并的手工/官方APNIC CN IPv4 CIDRs同时给普通App和软件热点；热点私有FIB先批量安装 route，再发布转发规则，Stop/Restore先撤规则再批量删路由，读回索引避免逐前缀全表遍历。沿原软件热点及真实 Android 下游/内核出口语义，不新增数据路径；真实出口和性能尚未验。
- 新普通测试APK `org.wbdnext.testtraffic`，与WBD产品不同UID；普通TCP/UDP socket逐字节验证、首回包/RTT p50/p95/p99、并发双向流式echo、可选系统DNS；IPv4/IPv6目标；同一代码先在Host loopback，再打包独立APK。无Root/VpnService、不会自动配置或部署设备/服务器。CI复用现有APK job，产物与产品一起收集；历史源码门后置，不把失败改记成功。
- 按真实B81 FAIL修旧断言和已存在的regex-lite依赖图。设备/性能、B82签名APK仍待同源Actions；历史A48 SYN/SYNACK/TLS/认证/租约/M4 RAW/TUN双向/Stop观察不变。
- 当前主体开发可候选冻结；不把热迁移、idle dormant、在线规则下载、Private DNS/DoH、硬件热点offload、FakeIP当当前真机测试前置。下步收本SOURCE CI并集中授权ARM64测试，详见 [测试矩阵](../../plans/ANDROID_ROOT_TEST_MATRIX.md)。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Shared CN IPv4 direct routing for software tether, cold batch routes and readback; separate ordinary Android UID TCP/UDP/OS DNS test APK and source-specific test matrix."}
```
