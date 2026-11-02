# PLAN027A H974｜MSS Linux原Go装配仅允许两份源锁测试覆盖

H971[41482859398](https://github.com/lly8666/wbd-next/actions/runs/41482859398) 进入Linux编译前已成功运行统一7文件安装器，下一步 `for r0/go_overlay/internal/realityfront/*.go` 拒绝在原始 checkout 上覆盖旧`tls_test.go`。对比固定上游SHA发现精确2处覆盖：`tls_test.go`将测试常量DefaultMSS替为`PublicV4AdvertisedMSS`；`wire_qualification_test.go`还修`len(Payload)` uint16/int测试类型。这两份本来就在同一个 plan020 manifest 以**原始SHA/目标SHA**作为两条`replace`动作；旧自动复制循环只承认`create`，与实际装配策略不符。

新增test-only安装器，要求原始Go checkout SHA、当前overlay SHA均与唯一manifest完全一致，且文件内容**只能**是列明的1或2处文本替换；全员验证再覆写。除这两个 `_test.go` 之外仍严禁覆写任何原Go文件。同步入口与廉价测试触发必要的一次新编译。不改生产TCP选项、Rust预算、协议或版本兼容；H971/H972旧失败保留，1389/1389真原生仍未验。

```feature-impact
{"kind":"none","ids":[],"reason":"Allow exact two manifest-pinned test-only Realityfront source replacements in Linux Actions checkout, keeping all original production file collision guards and MSS product code unchanged."}
```
