# PLAN026 Windows NativeOwner：M0 任务授权审计（2026-10-28）

用户明确选择Windows方案B：Go保留已有FakeTCP/uTLS/TLS及Windows WFP/DNS/路由/Wintun设备冷管理，Rust DLL 独占真实 Wintun/Npcap 稳态I/O、M2/FEC/Game/Health；长寿命隧道支持低频Go重连和动态lane。要求先Normal/off整批代码与夹具齐再集中测真实性能，同一owner迁其他模式。M0唯一main写者；本次只写计划、入口与任务，不改产品、不声称测试通过。

审阅 wbd-next main `7c09b9396fb4d9086be212786758244172008a9d` 的 Windows `m0_native_v4_windows.go` / `m0_native_v4_peer_windows.go` / Game peer、`v4_windows_owner.rs`、scoped bridge、native Wintun packet lease 和统一Windows native WAL/OS事务；对照 pinned old Go `wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` 的 Npcap、Wintun 原生适配器，以及旧SameIDReplacement/Health逻辑。当前M0 cursor旧N0 `produced=0 ready=4` + 在途 run 是必须保留的旧SOURCE事实，本次不代写cursor为已完成。

新增[详细执行任务书](../../decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md)、[Rust NativeOwner架构](../../architecture/WINDOWS_NATIVE_OWNER_V2.md)。main registry M0分配新包、同步 project/AGENTS/START_HERE/M0永久提示词/hand-off/README/旧架构优先级说明。保留其他工位epoch/权限、旧资格与历史失败。

```feature-impact
{"kind":"none","ids":[],"reason":"仅任务发布/设计/长期接手文档；没有代码、CLI、GUI、产品功能/配置默认或资格变更。"}
```
