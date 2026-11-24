# A42｜Android API36 原Rust M4已启动，原Go紧接着退出

A41 SOURCE `e2decb289a80dc38159a9d1a36f60afc56a918ef` 用户自行提供172条固定脱敏事件、三次Start：真实Root、FakeTCP SYN/SYNACK/Association、标准TLS（服务器身份校验**关闭**）、保护Admission、Rust Native Commit、/32真实内核读回、Native IPv4和Underlay绑定、RAW/TUN Attach、`M4_STARTED`连续三次均观察到。距M4_STARTED约81/71/88ms即原Go exit1，RST owned Stop_CLEARED；无原Go RX handoff、UID路由或真实App TCP/UDP。A41的/32已在真机通过，Rust M4启动不等于D2c通过。

审查`r0/go_overlay/internal/v4productcli/linux.go::runClient`确认M4_STARTED之后仍需：停同一原FakeTCP冷RTO、验证真实Association Detached、`RawIPv4Endpoint.ExcludeDetachedData`切换原AF_PACKET内核BPF，之后才进入`androidRootRouteAfterNative`。旧收据遗漏这三个短时错误点。新A42只在原Go实际失败返回处输出固定`COLD_RTO_STOP_FAILED`、`DETACH_STATE_FAILED`、`GO_RX_FILTER_FAILED`，成功点输出`GO_RX_FILTER_OK`、`GO_RX_HANDOFF_OK`、`UID_ROUTE_ENTERED`。原RootService锚定识别并输出脱敏枚举，Host JVM测试检查失败优先级与固定值；不造假wire、不更改真实TLS/认证/Rust加密/PhysicalNetwork/路由owner/Stop。无任何实体设备或个人服务器操作。

检查跨端：Linux原`waitOriginalNativeM4PeerProof`仅在`rotationGeneration>1 && sharedTun!=nil`时用于换代所有权，不是本次Android首次连接的70ms失败。Windows历史Ready门不应直接移植到Android；本批不改Linux/Windows公共建链判定。

下一步同SOURCE自动Actions完成原Go/Rust ARM64 APK、原Linux Oracle、Java Host和功能卡。由用户在获授权Android API36做**一次**Normal/off单测试UID Start并导出固定TXT：首看RTO、Detach、BPF或UID_ROUTE分支，锁定后直接修唯一原实现；获得UID路由后才验真实App TCP/UDP和完整Stop。TLS服务器证书身份验证仍需独立资格门。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A41 API36真机三次/32内核读回及原Rust M4启动后71-88ms退出；A42仅为真实原Go后置接收交接增加固定失败/通过类别。"}
```
