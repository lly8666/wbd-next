# A50 Android Normal/off minimal fast path

在已有A49b基础上删除接收DATA的checksum抽样；release不再逐包保存全部RAW头字段诊断；DNS接管未启用时不解析DNS53；每代连接只推导一次FrameBudget；唯一TUN reader已校验的IPv4长度/租约不再由私有seal API重复确认；M3-pending不再因IP校验和、DSCP/ECN、清除DF或options模板阻断后续AEAD。保留有界长度/头偏移、当前tuple、非首分片拒绝、M3/PN、generation、Stop。

## 资格与回归边界

- 施工分支：`experiment/android-temp-root-probe`，不直接修改main。
- 只移除无业务认证意义的前置完整性扫描/重复检查；不可越界的结构与记录长度、租约/generation、真正AEAD/PN仍执行。
- 目前仅有改动源码及静态测试；平台实际通过情况由当前source CI记录决定。不以BUILD_PASS冒称性能PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"减少加密DATA在原M3前的外层重复校验/诊断/预解析；真实CPU、吞吐、兼容性仍需同源跑测。"}
```
