# PLAN029B H2130–H2131｜Game4 明确高级 CN；Game2 不借 Normal

- B4 H2129 原 Action [44195727026](https://github.com/lly8666/wbd-next/actions/runs/44195727026) 仍独立 SOURCE `43f988d37edcb54e537b14d2f5a73aab4d6609fd` 原生执行，不重派。
- Game4 历史 [H2041 Action 43942345347](https://github.com/lly8666/wbd-next/actions/runs/43942345347) 在旧 SOURCE `60e4cc57e42be083d2338ae570749331b0e8b4b1` 有真正四 lane 原 TLS/Rust、CN物理 FakeIP Direct TCP32KiB/UDP 和 Tunnel 双向TCP/UDP、owned Stop 通过，**不能当新 SOURCE 029B Game4 已通过**；原Game4夹具新默认普通CN `cn-domain-direct=false`，旧高级FakeIP场景须明确 `--cn-domain-direct=true`。
- [H2130 Action44197234669](https://github.com/lly8666/wbd-next/actions/runs/44197234669) SOURCE `5e2cefce8da72c90975911dbe87a1646e4151589` **FAIL_CHEAP_PRE_NATIVE**：旧H1775静态断言仍匹配未带高级布尔的历史参数，且试图修改冻结 Go overlay 的 Game2 测试文件并缺功能影响留痕。没有原生Game4结果。
- [H2131 Action44197448012](https://github.com/lly8666/wbd-next/actions/runs/44197448012) SOURCE `2aa28ab92bf5ac324b556d65ab9b39801f6d49c6` 依旧 **FAIL_CHEAP_PRE_NATIVE**：旧H1775字符串已修，但 `prepare_windows_wiring.py --check-only` 严格拒绝原 Go overlay `m0_native_v4_game_cold_handoff_windows_test.go` blob不匹配。**不更新签名装配清单、不重建宿主**；把不必要的新Go测试恢复成原blob，只在源级静态测试检查原 Game2 `split-enable=true` 明确 OS Apply 前拒绝，Game2 不作实际Game支持PASS。
- 后续 Game4 单独签名 Action 仅用既有 `[plan029-game4-cn-real]`，真实四 lane/kernel/Stop 硬门与之前相同，不并入B4。不修改产品 Go/Rust/FEC/TCP/wire，也不宣称B5同VM CPU/GiB/p99已运行。

```feature-impact
{"kind":"none","ids":[],"reason":"Only signed Game4 fixture now explicitly selects 029B advanced CN and static test guard restores original frozen Go overlay. No production ABI/logic/UI semantics change."}
```
