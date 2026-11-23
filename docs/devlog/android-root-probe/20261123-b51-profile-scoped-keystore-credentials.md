# B51｜每套Root连接配置独立复用已有Android Keystore账号凭据

B50新四槽命名Root连接配置SOURCE `e5b4334b712208e94b1caa28c460de3f45aa12c0`，承接B49 [#45168583911](https://github.com/lly8666/wbd-next/actions/runs/45168583911) 11 SUCCESS/4 SKIPPED；B50产品 [#45171551179](https://github.com/lly8666/wbd-next/actions/runs/45171551179) 的正式 root-arm64-app Java变量重名 FAIL（详见B50日志），B51同批最小重命名 `namedProfileHint` 修复；不得用B49绿灯顶替。此前B50只存无秘密设置，切换不同Server还沿单份全局保存的密码/RouteKey，易误用前一个服务器口令。

B51直接复用已有 `RootEncryptedCredentialStore` 现成AndroidKeyStore AES-GCM记录、同一SecretKey和原 `RootSavedCredentialRecord` 格式，将默认槽外增加四个独立无备份AtomicFile：不改任何算法/身份策略/Go CLI。正式App保存槽位时保存相应有效密码/原始RouteKey到该槽，未填写时清除旧槽密文；载入槽位后只填本槽密文，缺失/不可读则清空密码/RouteKey以便用户填写，避免混用其他WBD服务器口令。删除槽位连同该槽加密记录。现有“清除所有已保存密码/RouteKey”同时清除默认及四槽后删除共用AndroidKeystore Key，当前已启动Root进程不受影响。原Service Root 0600临时文件、SessionID、标准TLS/账号、Rust M3/PN/M4和UID owner/Stop全部原样；没有新逐包路径、额外TLS安全门或CPU周期。

新B51源锁静态Gate校验原A38 `RootSavedCredentialRecord.encrypt/decrypt` 被默认槽和所有命名槽共同使用，Android原Keystore adapter随签名APK编译；旧A38 GCM/JVM test与B50配置codec tests保留。真Android多服务器账户切换/Network与应用业务、速度/CPU仍 NOT_RUN。仅实验分支/Draft PR #36，main和M0不改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B51四个Root连接配置槽各自保存/载入/清除密码与RouteKey，直接复用原AndroidKeyStore AES-GCM和RootSavedCredentialRecord，避免切换服务器误用上一槽凭据；Go/Rust/Stop不改。"}
```
