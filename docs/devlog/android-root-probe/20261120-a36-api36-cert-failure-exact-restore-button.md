# A36｜真机已到原TLS证书检查，增加APK精确网络恢复

用户自行提交SOURCE `4975c1abf4bc64357f3da246c85dcc15e84d9824` API36两次共76个固定事件：All Apps一次、Selected App一次；均原RST_GUARD_READY →真实FakeTCP Association →ClientHello TX→原RAW peer payload RX→`TLS_HANDSHAKE_FAILED_CERTIFICATE`，随后RST_MATCHED_DROP和STOP_CLEARED、owner cleanup。A34旧15秒无回包已跨越；原CA/hostname原因未知，原TLS验证/保护认证/lease/Rust M4 App双向/整机Stop未通过。

A36原Go使用 `errors.As` x509错误类型给出UNKNOWN_AUTHORITY / HOSTNAME_MISMATCH / EXPIRED / NOT_YET_VALID / INCOMPATIBLE_USAGE / INVALID_CERTIFICATE / OTHER_CERTIFICATE固定类别，及APP_PEM/OS_STORE信任来源。Android UI新增本地PEM文件选择、长度和X.509解析核验，仍交给原Go的0600 file和标准uTLS VerifyServer:true；不自动下载信任锚、不用InsecureSkipVerify。用户需自行确认原Linux服务器签发CA、证书DNS SAN匹配SNI。

APK「恢复网络」按钮先触发原有精确owner Stop，等待真实Go/Rust进程离开；root脚本复核0700目录、0600 owner.pid、PID启动时间和原ELF，只对同一活owner TERM；之后用签名当前APK哈希验证的原Go/Rust Bionic资产恢复，独立运行 `--android-recover-owned-root`。Go `rootjournal.RecoverOwned` 基于单UID/Group/AllApp v3/v4 root-only durable journal、flock和精确ip(8)读回撤销本项目私有表/规则；`rstguard.RecoverOwned` 只撤销本项目4元组RST DROP规则，未知/外国iptables marker和私有表占用必须拒绝。若空journal仅确认无本项目规则，不调用系统flush。Java仅收固定路线、RST、最终shell退出收据；任何不确定状态保留journal以供恢复，而非伪装成功。

首轮SOURCE `6e521f8601efc02e14a1b1d7f51f242bd429db55` 真实CI FAIL：`rootjournal/recover.go` 多余未用os import；A36b SOURCE `47a521e0d1f6d271ef5ac81851fceae8b57753ca` 代码复审发现用于proc stat第22字段的POSIX必须为 `\${22}`，故本次修正并保留失败史。新同源Host/原Linux Oracle/签名ARM64 APK及功能治理均待结果。没有操作用户的手机或服务器。A35 real phone success不得冒充A36恢复按钮已验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A36真机RST命中并进入TLS证书错误，新增不降级CA证书细分类、本地PEM导入及严格原Go rootjournal/RST一键恢复，原App真实业务仍NOT_PROVEN。"}
```
