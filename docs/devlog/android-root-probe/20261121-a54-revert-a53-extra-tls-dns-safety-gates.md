# A54｜按用户要求撤销 A53 额外 TLS/DNS 防御门，恢复原兼容行为

## 回退范围

用户明确要求：兼容性优先，不加未授权的安全检测、防篡改与防御式拦截。A53 提交 `bb11a95b98332b8885dda07b190435ab619e90b3` 自行改变 Android Root App 默认值和 DNS/TLS 依赖，属于不必要的行为变更。A54 将以下六个实际代码/Host 测试文件**原样恢复到 A53 前 B3c SOURCE** `a173939c41c183fa8df6048541037254323badba`：

- `android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java`
- `android/root-app/src/org/wbdnext/rootclient/RootClientService.java`
- `android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java`
- `android/root-app/ci/OriginalGoCommandArgsTest.java`
- `android/root-app/ci/test-network-scope-gate.sh`
- `r0/go_overlay/internal/v4productcli/linux.go`

效果：App TLS 服务器身份验证默认 OFF（可由用户勾选并导入 CA），B3 隧道 DNS App 默认 ON（可关闭）；老 Java argv 重载与 B3 默认一致，原 Go Android CLI `--android-tunnel-dns` 不依赖 `--tls-verify-server`。未新增身份校验、篡改检测、网络拦截或路由安全门。原 Go/Rust FakeTCP、标准 TLS 握手、业务账户认证、M3 AEAD/PN/replay、M4 DATA、owned Stop 以及 Linux/Windows 共享产品语义不改。

旧 A53 devlog 与 [Action #44894869324](https://github.com/lly8666/wbd-next/actions/runs/44894869324) 的成功范围作为历史保留，**不再代表当前行为**。本次仅改实验分支；main、M0 registry/cursor、真机/外部服务器均不操作。新 SOURCE 只能由其自己的 CI 测试确认构建资格；未经实际设备回执的 Android TLS/租约/应用 TCP/UDP/Stop 仍为 NOT_RUN/NOT_PROVEN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A54按用户兼容性要求完整回退A53额外TLS/DNS限制，恢复B3c Java/App/Go原始默认及功能；保留原协议和历史CI记录。"}
```
