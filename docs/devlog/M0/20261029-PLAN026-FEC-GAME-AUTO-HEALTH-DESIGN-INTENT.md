# M0｜PLAN026 FEC/Game/Auto/Health 执行合同与热文档精简

- **意图**：响应新授权，将 Windows NativeOwner 的 Fixed/Game、Linux/Windows Normal Auto+Keepalive、老服务端超时/FIN/DORMANT协同与 V2 测试次序具体化，给当前 M0 在main整批开发；同时缩短8文件热入口的滚动历史，原证据/决策不删除。
- **依据**：main阶段B研究、PLAN026原决策；`wobuzhidao@a7a82db3` 的 `adaptivefec/controller.go`、`runtimeowner/{health,quality,control_policy}.go`、`runtimeentry/{lifecycle_health,lifecycle}.go`；`wbd-next` 的 `v4_fixed_stream`、`v4_game_lane`、`v4_windows_native_runtime`、`bridge_v4_fec2_public_product_linux.go`；旧FEC W168 56case/250M与W103 Game证据、`WL_PERF_HARNESS_V2.md`。
- **取舍**：搬快升慢降和一次控制出口，不搬旧Go RS20 packet/wire/轮询；Rust唯一Auto控制，Game无Auto；空闲Keepalive与无认证超时/FIN休眠明确区分；Fixed/Game在Auto之前测，全模式复用V2监测点；软性能不过度设置硬阈值。
- **本提交范围**：只有方案、registry当前目标引用、长期提示词和热启动/章程文本；**产品代码、配置生效、夹具适配与Actions均未改、未跑**。M0按新施工契约写齐以后才冻结SOURCE跑测试；不是完成交付。
- **未验**：Windows Fixed/Auto/Game Rust-only真实I/O、双端Health与Dormant、自然Auto升降/同VM CPU A/B/物理资格均仍待同源新测试；旧历史PASS/FAIL不改判。

```feature-impact
{"kind":"none","ids":[],"reason":"本批纯施工方案与agent热文档压缩，没有产品能力、用户参数或默认值实际改变。"}
```
