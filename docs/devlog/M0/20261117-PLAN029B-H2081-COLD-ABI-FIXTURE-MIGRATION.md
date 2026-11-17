# PLAN029B H2081｜修正旧测试期待与新029B真实规格不一致

H2080 有独立的 `r0-cross-abi`、`r0-native-abi`、`native-functional`、Governance 通过。真编译Go原测试 `TestPlan029GoV3TrialOnlyOwnedCIAndExplicitValidatedDomains` 仍期待 `split=false` 返回nil/旧V2，和029B明定的“关闭业务Direct资源但保留Rust V3公共DNS/启动padding”相冲突；改期待为V3 all/PolicyFlags0，无CN/Direct表/假IP持久写者。Rust 旧测试 `config()` 仍填cold.version=1，新正式ABIv2会拒绝，导致9个测试本身初始化失败；仅修该测试helper version2，不改生产V2拒绝旧版本的严格边界。相应Go overlay `result_blob` 精确同步。

原 H2080 failed Action 继续保留，H2081尚未有实网或原 GUI 资格，不标 B0–B5 PASS。严格保护 H2077 旧产品日常 PASS_SCOPED；下一步优先收新SOURCE生产编译和原正常模式回归。

```feature-impact
{"kind":"none","ids":[],"reason":"H2081 adjusts two pure test expectations to the intentional versioned cold V2 and split-off Rust V3 base, no product feature implementation changed"}
```
