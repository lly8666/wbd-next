# Linux/Windows shared minimal outer DATA parser

Linux AF_PACKET RAW batch/legacy reader和Windows Npcap正式DATA接收改为单次轻量解析，不再对收到的加密DATA逐包扫描完整TCP checksum或以可变DSCP/DF/options模板提前拒绝。仍验证20B IPv4/20B TCP长度、当前tuple、未分片、DATA flags、MTU。原M3 AEAD/PN是唯一业务交付判断。纯ACK/SACK没有M3认证，保留短包checksum与范围检查。按固定头flags分类避免重复DATA/ACK解析。原strict公共解析器供测试诊断，不改Go标准TLS/AEAD/wire/owner/Stop。

## 资格与回归边界

- 施工分支：`perf/outer-rx-minimal-parse-20261121`，不直接修改main。
- 只移除无业务认证意义的前置完整性扫描/重复检查；不可越界的结构与记录长度、租约/generation、真正AEAD/PN仍执行。
- 目前仅有改动源码及静态测试；平台实际通过情况由当前source CI记录决定。不以BUILD_PASS冒称性能PASS。

```feature-impact
{"kind":"updated","ids":["linux-raw-tun","windows-native-transport"],"reason":"减少加密DATA在原M3前的外层重复校验/诊断/预解析；真实CPU、吞吐、兼容性仍需同源跑测。"}
```
