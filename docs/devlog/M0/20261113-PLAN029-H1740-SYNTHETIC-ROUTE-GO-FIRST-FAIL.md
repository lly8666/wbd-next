# PLAN029 H1740｜首个Windows Go原产品编译FAIL精确修复

- H1739 SOURCE `5b36599370e0b9ac2a368407befd77ba53cedefc` [原Go no-WFP WAL编译43409673563](https://github.com/lly8666/wbd-next/actions/runs/43409673563) **FAIL**：`native_plan029_no_wfp_routes_windows.go:45:28 plan.Physical.Source4 undefined`。原donor的`PhysicalPath`没有Source4字段，不是路由/Defender实网失败；[Windows源构建43409673369](https://github.com/lly8666/wbd-next/actions/runs/43409673369)亦FAIL，原日志和对应SOURCE保留。
- 仅把synthetic /32源冲突检查的假字段换为已有`plan.Physical.NextHop4`，Rust`NativeTcpActor::safe_synthetic`仍按实际`physical`与`lease`拒绝重复。/32依旧可选、必须在已有第4个routes v2 WAL的逐key CAS账本内，默认不安装。Go装配manifest新result_blob同步；不变更旧M4冻结材料。
- 该SOURCE Windows Go新Action待验收；真实原Go+Rust完整Direct TCP仍**禁止启用**，因为需要精确owner Defender Allow与OS Apply后的正式Native激活，D1–D5/P1–P2未运行。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fix first native Windows Go compile failure for synthetic TCP /32 route (original PhysicalPath has no Source4) and keep exact H1739 failed evidence"}
```
