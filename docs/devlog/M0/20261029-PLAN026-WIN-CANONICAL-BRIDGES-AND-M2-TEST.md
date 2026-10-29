# M0 PLAN026｜原Go WBC4 Bridge 单份装配，Windows M2共享测试收口

2026-10-29：SOURCE edfec92 后 `40818630086` 原Windows Go装配成功但 Go 编译曾被缺少 `V4WindowsM2Effective`、`ReadBoundOriginalM2Effective`、GameFec batch方法挡住。两份代码已存在于当前SOURCE的 `bridge_v4_windows_m2_effective.go` 和 `bridge_v4_windows_game_fec_batch.go`，只是没有进入旧 WAL 工作流使用的 `manifest-plan020-m0.json`。本提交把两份精确Git blob纳入这一份权威manifest，并从新版Windows预检的 `EXTRA_BRIDGES` 移除相同二次拷贝。全部原凭据TLS、FEC2/Game crypto、真实WFP、Os WAL行为不变。

同期 Windows original Rust Owner 的专项测试在真实共享 `m2_global()` 修复/回执分配器上并行运行，测试中的 `cold()` 用同一个人工代次/隧道身份，产生互相抢占；此前 source d41 的13项中12通过，source06bc的13项中11通过，**都不应涂改成全绿**。仅对这个 Windows 原owner专项执行 `--test-threads=1`，保持所有严格原断言、原始全功能E2E/其他Rust回归默认并行，不用生产逻辑伪造独立键。若单线程仍失败，需处理真正ERR而不是继续缩小测试范围。

本提交仍非 Windows Game NativeAttachV3 / Server FIN Dormant/Wake / Linux RustAuto完整产品；不启动完整Fixed/Game/Auto V2网络矩阵；所有尚无同源真实测试的产品保持NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"两处已有Go桥的原源装配一致性修复和人工共享M2测试环境串行，不修改产品包路由、配置或资格。"}
```
