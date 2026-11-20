# A38｜抓到实际TLS验证覆盖；设备加密持久保存密码/原始短RouteKey

## 实际用户设备诊断：A37表面DISABLED却证书校验失败
用户自行用A37签名SOURCE `033d96f81535a5a1c5a7ffe3b6075eb82b1e3227` 在API36导出81个固定事件（All Ordinary Apps IPv4一次、Selected UID一次）。两次都明确 `ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED`→原 RAW SYN/SYNACK/Association Established→真实TLS bootstrap TX/RAW Peer Payload RX→`TLS_HANDSHAKE_FAILED_CERTIFICATE` + `TLS_CERT_REASON_UNKNOWN_AUTHORITY`，两次RST guard匹配且STOP_CLEARED。证据表明A37默认开关未覆盖最终原握手。

定位 `r0/go_overlay/internal/realityfront/admission_v4.go` 真正 `handshakeClientConn` 前有 `tlsCfg.VerifyServer=true` 无条件赋值，覆盖 `linux.go` 来自主线 `--tls-verify-server=false` 的配置。这是实际认证路径强制证书验证的根因，不是原服务器证书突然有错。A38删除强制覆盖，仅尊重已有显式CLI opt-in。新增从最终握手tlsCfg导出的固定安全事件EFFECTIVE_DISABLED/ENABLED，不泄露SNI/证书或密钥；Host Go测试实际运行自签名服务器的原TLS1.3 + protected admission：OFF无受信CA需完成，ON无CA需拒绝，ON且信任CA需完成。所有原RouteKey/原用户名口令/租约/原Rust M4与kernel RST守卫保留。

## 设备凭据体验与安全

用户要求密码与简版RouteKey多次START或重开APP无需重复手输。新增 AndroidKeyStore AES-256-GCM（独立随机IV+认证AAD）加密快照，存 `getNoBackupFilesDir` + AtomicFile + 0600/owner/inode检查；只包含原始UI输入的密码和短RouteKey（或合法传统64Hex），以便恢复原短Key；不会将原始RouteKey写入旧的只存派生值v2缓存。点击START在校验成功后加密保存，界面不再在START后清空；增加手动保存/清除两个按钮，首次建UI从加密记录恢复。秘密不会进Intent/argv/root stdout/SAFE TXT/Android备份。清除删除本APP快照和Keystore密钥，不动服务器、其他App、现有WBD内核规则。Android Keystore不可用或记录遭篡改时拒绝静默明文回退。Host JVM测试是真AES-GCM加解密/篡改/错误Key/格式/非法Key，AndroidKeyStore本机API尚未在guest/手机执行。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A38真实A37 API36日志证实证书禁用但握手仍UNKNOWN_AUTHORITY；删除admission_v4隐含true覆盖、原TLS三态Host测试，新增AndroidKeystore加密持久保存密码/简版RouteKey。"}
```

## A38a 同源测试预审发现必需参数，提前修复而不放宽原保护Admission

A38新增真实Original Go Protected TLS三模式测试在编写后自检发现测试构造应和现有 `v4Pair` 一样：原 `EstablishServerV4` 必须传入合法 `NewV4EpochStore`，而受保护的 `TunnelID` 必须精确16B。首个A38测试fixture原本遗漏 `V4ServerOptions.Epochs`，并使用17B示例tunnel id。这些都只能在真实Go保护认证中直接FAIL，并非 TLS 开关回归。现把同一个真实原测试配成合法真实EpochStore及16B tunnelID，**保留原协议的所有严格长度和epoch条件**；再独立复跑同源码CI。此前产品SOURCE `81649ee12b8fb9fa9ba048c0fe355e85a292ff26` 的历史结果照实记录，不冒称测试成功。

## A38b 功能卡闭环，不触发新产品构建

SOURCE `a2c7b33a2fadd57dcbd89bca1163b4fb14f6d691` 的 [治理 #44726819409](https://github.com/lly8666/wbd-next/actions/runs/44726819409) FAIL：只更新devlog测试预审，附带原有feature-impact但没有同提交更新feature卡。此仅文档修订同步A38最终发现、主线证书默认风险和设备Keystore私有持久化范围，52条历史验证记录完整保留，卡小于16KiB。产品Go/Java不变，产品同源构建仍使用 `a2c7b33a`，真实用户Android根认证/业务/恢复均NOT_RUN。先前 `81649ee` 产品CI因新SOURCE替代而cancelled，不能当PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A38b按治理same-commit要求实际同步feature card到已提交的有效TLS校验修复与Keystore UI持久化，保留52条历史。"}
```
