# M0 H2328 · Game/Linux native audit 的两处具体 schema 错误（测试修复，产品冻结）

## 冻结与错误分离
- 当前 main 30-case Game/Normal 测试源 `71e8304532f77236f4aa635afd9f4d004eba2db2`。**这一 SOURCE 的真实二端运行不因本纯测试工具修复改变 SHA，也不能冒充本补丁 SHA 重新测试。** 旧 artifacts 的 native PASS 与审计脚本 FAIL 独立登记。
- Linux↔Linux 客户端/服务器 18 场景：原真实 GoTLS client+server/Rust/ISA-L bundle 编译、Rust 单元与三个产物 SHA 均 PASS；旧打包 validator 误读 `manifest["source"]`，实际版本字段 `source_sha`。独立 H2326 分支 `d5c64d2` 已成功编译并开始 18 个真实原生场景。main 现同步其两处 workflow+一处 adapter 正确字段；只读 manifest，不放松 SHA。
- Linux Normal 0/1/5/10/20/30 双向真实原生都已 PASS（来源于 `d5c64d2`，**非本 main SHA**），client/server R/F：0/0，0.434/0.436，2.384/2.360，5.391/5.494，8.904/8.904，8.932/8.932（单位 %），全部 netem 双向实际 drops、Stop/清理成功。未来 main 独立 SOURCE 仍待测试。
- Linux Game2 原生在 d5c64d2 的 5% 场景真实 `PASS_SCOPED_OBSERVATION`，client/server 各 `outer_data_retransmitted=388`，双端 readback `outer_repair_native_verified=true`，Stop/netem 和业务真实 PASS；但是新增解析器误调用 Normal 独有的 `recovery_policy_verified`，错误标 `OUTER_ON_NOT_AUTHENTIC`。main 和 H2327 分支都修为按 mode 分别读取对应真实原生验证字段，仍要求每个 client/server 自己的 F/R 或 Game counters。
- Windows→Linux Game2 FEC OFF 5%/30% 和 Game4 OFF 5%/30% 旧 12-case 控制 job 红色，原生 Windows→Linux 运行全 PASS/双端 Stop，原因只是解析器错用 `WBD_GAME_NORMAL_SHARED_OUTER_STOP`（**Windows** Rust 标记）解析 Linux server。原 Linux server 有两份互证：Go `V4_PUBLIC_GAME_OUTER role=server...` 与 Rust `WBD_GAME_{OFF,FEC}_LINUX_NORMAL_OUTER_STOP copied_appearance=N first_record_wire_bytes=F copy_record_wire_bytes=R`。main 审计器现同时要求两份真实来源一致、`R/F<=10%`，并保留原 Win Frozen 承认计数、parity 完全分离。
- 0% Windows Game2/4 FEC OFF Linux server 仍分别 364/727 次定时外层复制（双向真实 100% 交付），约 0.23%–0.24% 原首发字节；Windows only 2/1 次。与 Normal 0% 零外观差异显著，是**待评估模式策略**，不是 FEC parity。Game2 fixed6 Windows 即无损也复制约 1519 次，Linux约 374 次；此为真正数据，不因自动化 PASS 解释为零额外成本。
- 全部仅变更工作流/报告核对，不修改旧 M2 退役、本轮原始 Go/Rust 产品、发送预算/默认值；尚未获得全部 Game 12+12 场景的完整双向资格，不能推广为双向全模式 PASS。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Correct original native Windows Game/Linux Go Rust dual-stop evidence parsing and Linux source_sha plus mode-specific readback; no product, ACK, FEC or outer-repair policy behavior changes."}
```
