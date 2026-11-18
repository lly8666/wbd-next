# H2178｜PLAN029 Linux双原生ISA 10/10 原生签名后的治理预算补账

源锁 [H2177原生Action 44258876671](https://github.com/lly8666/wbd-next/actions/runs/44258876671) 两独立job native x86_64/aarch64，各一次原Go TLS+Rust+ISA-L构建及五个Linux服务端和客户端双netns测试，全**10/10 PASS_SCOPED**；[原证据](../../evidence/M0/PLAN029-H2177-LINUX-X86-ARM64-TWO-ENDPOINT-FIVE-NATIVE-PASS-20261118.json)中有二进制SHA、原内核TCP/UDP、MTU1460、FEC6两端各96条parity、Stop。原SIG SOURCE 3cc095e38d98fd1a9b2a8f00835b113bc434c9e1。**不在新文档提交上重跑网络，更不能以新文档SHA冒充原生SOURCE。**

H2177归档提交73a828e触发 [治理Action44260485192](https://github.com/lly8666/wbd-next/actions/runs/44260485192) 与维护回归：`tools/governance.py.validate_repo`拒绝M0热文件合计**33430B > 32768B**，使结构、feature gate及部分test_governance因预算先于角色/epoch验证而连锁FAIL。此为提交热入口字数超限，**非**原产品网络/Stop失败。遵原仓库守卫，不改`.governance/policy.json`上限或治理代码，只压缩M0游标的冗余进度、保留最新3篇devlog及唯一H2177同源证据，压缩START_HERE重复历史说明但保留关键受限PASS、硬门与入口。

原则：不改变产品Go/Rust、GUI、真实网测、旧签名FAIL或029/029B完整技术OPEN，030不启动。治理新SOURCE结果需新Action单独核对；不能把静态门禁绿灯声称是第二轮Linux实网证明。

```feature-impact
{"kind":"none","ids":[],"reason":"Only compact duplicated M0 handoff/cursor prose to satisfy the existing 32KiB hot-read budget; preserve H2177 signed Linux functional source and all product/feature behavior."}
```
