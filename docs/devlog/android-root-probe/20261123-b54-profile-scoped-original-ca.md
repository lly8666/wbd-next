# B54｜每套Android Root服务器配置独立的可选原Go TLS CA

## 基线和真实缺口
B53四槽SAF迁移、B52原生跨配置Stop→START基于B51a `09aa7049ebbb5f157ef3158687b5c943d69150fe` 已获双ABI/签名APK/Linux原Oracle [#45172614955](https://github.com/lly8666/wbd-next/actions/runs/45172614955) 11 SUCCESS/4 SKIPPED；B53本SOURCE CI见 [#45183645532](https://github.com/lly8666/wbd-next/actions/runs/45183645532)。原Root App已按槽保存Server、Go TLS SNI、密码和RouteKey，但B23可选的TLS CA在 Activity 中只有**最后一次全局**值：如果用户连接两台各自使用私有CA的WBD服务器，B52冷切换可能仍把前一服务器的CA交给原Go。

## 本批直接修功能，不另建验证框架
- 新 `RootConnectionProfileCAStore` 只把现有用户自己导入/粘贴的 **PEM公开证书文本** 存到对应四个本机 noBackup 配置槽，沿原 `RootPrivateCredentialContract.CA` 的同一1MiB长度上限；不加密公开CA、不改SSL库、CA格式或标准TLS流程，也不启用默认关闭的严格服务器证书验证。
- 保存命名配置时按槽保存对应CA；载入配置时将 CA + 同槽账号/RouteKey/原设置一起更新**冷UI**，同时维护单份 `wbd-current-ui-ca.pem` 仅供 Activity 重开后按最后选中的服务器回填，空内容表示“该服务器无自定义CA”。旧版本没有该文件时，仍调用B23原私有CA恢复，兼容以前的单服务器使用。
- 导入本机新CA、显式清空CA、正常START时同步UI召回文本，但 `start()` 的实际 `privateText(wbd-server-ca.pem,pem)` 仍是原Go唯一TLS信任入口，并且仅在用户自己勾选 `verifyTLS` 后才传入。更新 UI记忆失败不能成为新连接被拒的门；运行中的Go/Rust owner、RAW/TUN/UID/Stop不受载入配置影响。
- 删除命名槽时同时删除该槽CA（不清其他槽）；B53四槽无密钥SAF导出继续**不包含CA**，所以跨APK安装后的私有CA仍须用户从原文件重导。新增旧真实APK编译/生产源门检查 CA 槽读写与原Go handoff，未增加Root Service线程、Go逐包FFI或Rust数据面成本。

Android实体双服务端私有CA/切网与应用TCP/UDP E2E继续 NOT_RUN；BUILD/HOST仅按本B54 SOURCE最新Actions单独验收。不更改main、M0或任何物理机服务器。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B54按四命名Root配置槽保存/回填原有可选TLS CA，切换服务器不继续用上一槽CA；默认TLS验证开关、原Go标准握手及Rust数据面不变。"}
```
