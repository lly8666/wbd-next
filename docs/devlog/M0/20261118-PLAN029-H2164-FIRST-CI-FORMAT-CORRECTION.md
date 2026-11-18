# PLAN029 H2164｜H2163 自动检查首错限域修复

H2163 source `cb8d81b7338d4d46ebe24dcead86b2a2bbe1877c` 自动[Action44241101644](https://github.com/lly8666/wbd-next/actions/runs/44241101644) 真FAIL：feature_catalog首错 `dns-split-ipv6.json` UTF-8 16778B > 16KiB；governance首错 M0 cursor context_refs 9 > 8。原失败不删除，非产品网络故障。

本次仅压缩功能卡新写的使用描述（历史 verification/FAIL/NOT_RUN不删），cursor 上下文恢复8项；保留用户可见设置与H2162 H2135原签名资格。治理阈值不改，不动Go/Rust/ABI/GUI二进制/热路径；本SOURCE新Windows编译和业务NOT_RUN。029/029B用户日常PASS_SCOPED，技术OPEN；030 NOT_STARTED。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Keep existing signed scope and original failures while reducing UTF-8 card bytes under the unchanged catalog limit."}
```
