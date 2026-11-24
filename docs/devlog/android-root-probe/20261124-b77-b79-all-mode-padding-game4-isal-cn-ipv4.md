# B77–B79 Android 第一/第二批合并接线

- feature-impact: android-root-native-client
- 基线 `7dfc93fdfcb9b0c46e134ab234004db77822a2eb`，仅 experiment/android-temp-root-probe，Draft PR #36。main/M0 未修改。
- B77：Normal/off、Fixed、Auto、Game2/4 off/fixed 使用既有原 Go TLS startup padding mode、原 Rust 源包封装及 GameAdapter，off 不建立跟踪表；FEC parity/Health 不填充。Game4 immediate/short/wide，默认宽错峰；App/Service/CLI/四槽及导入导出保存，旧设置兼容。
- B78：原 ARM64 release Rust native_fec_acceleration 链接 Intel ISA-L 固定 revision c387163fcbca62701d646149564c550c78a4f985 的 NDK Bionic 静态库；x86_64 CI 保持 scalar，构建及实体 SIMD/性能尚待验证。
- B79：原 APNIC CN IPv4 allocation snapshot (20261116) 生成器、签名 APK 数据/来源摘要、显式配置、Go冷合并与16条手工 CIDR 分离、已认证会话 UID 私有 FIB 内核 throw 批量安装与同一 journal Stop/Restore；整表匹配由线性查找每条变为索引匹配。CN分配表不保证精确地理位置。仅普通App IPv4 UID路由，不声称热点CN、强制所选物理Network出口或高级域名FakeIP；DNS独立配置，绕开TUN的目的地址DNS不由Rust捕获。
- B75/B76 [产品CI](https://github.com/lly8666/wbd-next/actions/runs/45335592476) 9 SUCCESS / 1 FAIL / 5 SKIPPED；旧APK源码断言计数3→4，本批同步新实际调用链判据。[功能目录](https://github.com/lly8666/wbd-next/actions/runs/45335592604) SUCCESS。
- B77–79 同源 CI 待判，设备和性能 NOT_RUN；Android 全模式外层机会式重传、高级CN FakeIP仍未完成，不加虚假开关、不宣称已接线。
