# A37｜与main一致：APK默认不验TLS服务器证书，严格校验可选

用户指出主线默认不验证TLS服务器证书。核对main `2e615b90` 原 `r0/go_overlay/internal/v4productcli/linux.go` 有 `--tls-verify-server` 默认false和 `ClientConfig.VerifyServer=c.tlsVerifyServer`；实验SOURCE `09910ee1` 强制了true，用户真机两次原FakeTCP/RAW TLS成功收包但证书校验失败。A37仅实验分支修原Go默认false与可选true标志；Android APK增加默认未勾选的严格验证框，完整传入Service→原CLI，严格模式才传应用私有CA PEM，Go公布固定 `TLS_CERT_VERIFY_MODE` 的DISABLED/ENABLED枚举给安全TXT。Main不改。

默认TLS服务器证书不验意味着**不验证对端身份，存在中间人风险**，但依然走真实TLS握手和原WBD保护认证，不伪造ready或放宽Root网络范围。严格模式可使用系统信任或显式私有CA。A36一键精确恢复按钮、RST守卫、Android UID/32、原Rust M4不变。

同源测试：原Go parse默认/opt-in、Java argv默认/opt-in/CA、固定诊断、安全门、ARM64 Go/Rust签名APK及Linux真实Normal/off Oracle。A37真实Android握手、认证、M4和Restore仍NOT_RUN。不得把默认无证书校验说成已认证服务器。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A37严格按main --tls-verify-server=false恢复APK默认不验服务器证书，保留严格opt-in与固定诊断，路由Key/保护认证/M4未改。"}
```

## A37a Feature catalog 对同提交卡片的约束

初次产品源码 `033d96f81535a5a1c5a7ffe3b6075eb82b1e3227` [治理 #44722429636](https://github.com/lly8666/wbd-next/actions/runs/44722429636) **FAIL**：devlog 的feature-impact声明了已更新android-root-native-client卡，但该提交实际未改卡。这里仅修改功能卡摘要/风险说明，并在同一提交更新该devlog，不改Go/Java/Bionic/APK产品文件；原52条历史verification全部保留，卡UTF-8字节数受16KiB限额。产品验收仍以独立触发的 `033d96f` 同源码Action为准，不能把这次治理结果冒作新版APK。
```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A37a将此前declared的主线默认不验TLS证书事实、严格opt-in和MITM风险实际写入同提交卡片，保留52项历史。"}
```
