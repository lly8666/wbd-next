# A33｜API36 A32真实回报后：SYNACK候选与15秒TLS冷失败分段核验

## 真机输入、精确证据边界

用户自行运行 A32 SOURCE `3e2c0cfd7a9dff5598f1c7a33ab6eaaff9e3d67b` 的签名ARM64 APK（API36），只读安全TXT有29个固定事件：`APP_PRIVATE_CREDENTIALS_0600_VERIFIED`→原 Go `ARGS_ACCEPTED`→`TUN_OPENED`→`TUN_KERNEL_CONFIGURED`→`RAW_SOCKET_READY`→`COLD_SYN_TX_OK`，随后约1.1秒出现 `ORIGINAL_GO_TCP_SYNACK_SEEN`，再约15秒后 `ROOT_PROCESS_EXIT_1`。服务端/32私表readback NOT_OBSERVED，Rust M4/应用TCP UDP/owned Stop NOT_PROVEN。

审查证实旧 `ORIGINAL_GO_TCP_SYNACK_SEEN` 来自 `RawIPv4Endpoint.ReadSegment` 过滤后的SYNACK及MSS检查，**发生在原 `ClientAssociation.HandleSegment` 前**，故严格称 SYNACK **候选**，不直接证明原Association Established或Linux原server已经验收。旧 `last_session_stage=ORIGINAL_GO_TUN_OPENED_CONFIG_BEFORE_RAW` 与29事件矛盾，是 `RootDiagnosticReport.stage` 在V2非零退出分支中优先返回早期TUN的真实报告逻辑Bug。SYNACK后15秒匹配 `ClientAdmissionConfig.TLS.Timeout=15s`，但不能凭时差认定故障是超时/证书/route-key/服务端。

## 本批小而多层的诊断，原协议与冷拒绝不改

- 原 `runClient` 在真实 `waitForOriginalColdSYN` 返回nil后额外输出**Association Established**；原产品对象初始化 success/failure 另外标记。绝不把RAW SYNACK候选冒作Established。
- 原 `EstablishClientV4` 只在Android客户端冷路径输出TLS handshake attempted/verified/failed、TLS保护下Admission request write ok/fail、reply parse success/fail、完整Admission verified；失败严格固定 `TIMEOUT/CERTIFICATE/PEER_CLOSED/AUTH_REJECTED/VERSION_REJECTED/POLICY_REJECTED/OTHER`，绝不输出原错误、SNI、IP、密码、key、证书文本，失败不设成功标记。Windows/Linux 默认代码路径不输出新增Android标志，Go标准TLS/uTLS与证书/routeKey、原M1/M3/M4/PN/AEAD均不改。
- 真实Java RootService仅匹配锚定原Go固定行→原安全收据枚举；报告在V2非零退出时优先显示最深已证阶段或具体TLS/Admission失败，而不是TUN。不改变已导出的旧TXT历史事实，仍不升级系统DNS/netd/UID/data/Stop。
- Host测试覆盖 Go固定error classifier、Java marker anti-spoof及20种V2失败/阶段优先级（包括用户这次的TUN→RAW→SYNACK候选→exit1），同源码正式 ARM64签名APK/真实 Linux normal/off oracle。只有Android用户自主复测才能证明真实新阶段，不运行KSU/TAP、用户手机或联网服务器。

## 下一唯一外部资格门

使用新SOURCE signed APK（确认旧Root owner Stop/路由无残留后卸载旧debug签名版本），单次Normal/off、单独测试App UID的最小安全TXT复核：若ASSOC未建立，先查原RAW与实际peer；若TLS失败，按TIMEOUT/CERTIFICATE/PEER_CLOSED精确分流；若TLS verified但保护回复失败，按AUTH/POLICY/VERSION/timeout定位服务端。只有真实保护回复与/32内核readback通过，才继续原Rust M4/真实App TCP UDP/Stop，严禁用 Linux oracle/构建替代真机E2E。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A32用户API36真机已到原TUN/RAW/SYNACK候选、约15秒退出；修V2报告阶段优先级并在原Go真实Association/TLS/保护Admission多节点增加固定脱敏错误类别，保留原协议与业务资格边界。"}
```
