# B20｜Android Root App 实时读取原生 Fixed/Auto Requested/Applied

基线 SOURCE `95a80d8330a11d7d76c91459f6cc0c888e17b23a`（B19b）。上轮已把原 Go FEC2 Auto 策略/同一 Rust FixedStream 真改档接至 Root App 并有签名APK和Host证据；但旧UI只显示用户选择的模式。真实原 `V4PublicFecReadback` 状态在 client Run 结束时才输出，正在连接的App无法看见请求、PENDING、生效档位的区别。

- 原 `r0/go_overlay/internal/v4productcli/linux.go`：复用已有1s Health/业务 pulse，并在其4s M4数字观察窗口 **同一 control path** 调用 `native.OriginalFECReadback()`。首次观测或当前真实 revision/profile/pending 变化才输出单行固定原生状态 `V4_PUBLIC_ANDROID_FEC_STATE role=client mode=... requested=... applied=... profile=... pending=...`。Normal/off不开此 FEC 查询；无新增线程、clock或逐DATA Go/CGo。
- 原正式Root App在 `RootClientService` 读取已有原Go stdout，只认 `OriginalGoMilestones` 允许的固定消息，使用新生产纯Java `RootFecStateBrief` 解析可比对的 mode/请求版本/应用版本/档位/PENDING，向 `RootClientActivity` 的原1秒UI刷新展示，单独于NATIVE_M4_READY。新会话重置显示，退出后标记已结束；不把选择Auto/Fixed/已读配置当成真实 native APPLIED，不声称手机TCP/UDP/E2E。
- 原Host Java gate直接编译和运行新正式解码器测试，含Go时间前缀、Fixed/Auto、新档PENDING/APPLIED、版本与profile输入校验；原Go源码实际FECReadback的调用关系和Service/Activity接线也纳入现有Host门。Signed APK从正式 `android/root-app/src` 编译，无额外DLL/驱动/协议。
- 仅更新当前功能卡真实状态，不改TLS/AEAD、原FEC parity/source/PN/Stop或Android系统DNS；无实机/服务器操作。此SOURCE构建/Host通过须以新 Action 为准；应用交付、Auto真机修复和性能仍 NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B20 original Go periodic FEC native readback on existing Health loop and Root App live Fixed/Auto pending/applied version display with production Java host test"}
```

## B20a｜Host源码门的变量顺序修正

SOURCE `5b7e1b28eff5c4918e2cb3122af9550fcc881b35` 的 [Android运行 #44936625032](https://github.com/lly8666/wbd-next/actions/runs/44936625032) 原生ARM64/x86、纯Java `ANDROID_B20_FEC_NATIVE_REVISION_STATUS_HOST_PASS`、M3/DNS Host均通过；`root-arm64-app` Job因Host Python源码检查第29行的 `a` 在赋值前被读取而失败（`NameError`），正式APK打包步骤SKIPPED。此提交将该单条断言直接读取实际 Activity 文件，不改变产品Go/Rust/Java，实现与原失败记录保持不变；治理所需的同批功能卡已更新。新SOURCE通过与否依新Action，不造实机 E2E。 
