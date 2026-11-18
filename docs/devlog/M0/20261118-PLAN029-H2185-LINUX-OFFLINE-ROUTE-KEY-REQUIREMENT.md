# H2185｜Linux非Win能力合同：X25519无路由键并未接线，单测AES256＋真实MTU1280

[H2184 Linux原生x86+ARM Action44268654320](https://github.com/lly8666/wbd-next/actions/runs/44268654320) SOURCE `0650e6caf7e33b899fd3de91b45bcda4cbfb8ab8` 已各通过7个原Go TLS/Rust M4双端网测（6个Game2/Game4 startup-padding off/tls/flows/FEC/outer-off/immediate + Normal AES128）。最后第8场错误尝试`--route-key`缺省、X25519在线引导同时要求AES256/MTU1280，服务端原始日志在TUN创建前直接拒绝：`offline 32-byte route-key is required locally (64 hex characters); no network key bootstrap`，两ISA一致，**不是AES256失败、不是MTU1280失败，也不是随机填充失败**。当次整个Action FAIL保留。

H2185严格按**当前Linux CLI公共真实能力**拆为`normal-aes256-mtu1280`，使用原脚本临时受保护的`0600 route-key-hex-file`（客户端和服务端本地离线配置一致），保留当前真正的Go TLS证书/密码认证及Rust原AEAD；对`--outer-mtu 1280`执行同双netns真实系统TUN与TCP/UDP、MTU/DF边界、原Stop。X25519无密钥网络引导在Linux此源码**NOT_WIRED**，不得伪造验证；需要新产品设计后另行接线和真测。前一H2184手动IP动态MTU测试实际丢包也留存，正确的自动路径监督仅原`--auto-ip`客户端+服务端lease pool专用新夹具才能测。Linux Normal/Fixed/Auto `--startup-padding tls/flows`仍明确拒绝，不是Windows WinGUI能代替的能力。

只改本次Python互补测试请求与防回归，正式 Go/Rust 数据面和原填充内核copy验证完全未变。旧H2177基础10/10签名独立保留；当前完整技术PLAN029/029B仍OPEN、030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct Linux native supplemental test to use required local offline route-key for AES256 outer1280, retaining prior true no-key X25519 startup rejection as NOT_WIRED evidence; no product changes or relaxed business gates."}
```
