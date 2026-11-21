# A39｜A38真机0收据：修AndroidKeystore GCM IV和Start前保存阻塞

用户提交A38源码 `9a4ce82c5247fd3d099155759fe2d23223eac1ef` Android API36 `receipt_event_count=0`、`last_session_stage=NOT_STARTED`，完全没有UI/Service/Go内核事件（旧版本只在Service写事件）。因此不能推断Root、FakeTCP、TLS或对端任何失败，也不能确信设备点击过Start。

源码确认A38新UI在派发Service前**无条件同步** `RootEncryptedCredentialStore.save(this,secret,keyInput)`；其任何异常被 `RootClientActivity.start` 顶层catch转为START REJECTED，不产生事件。纯JDK加密单测未覆盖AndroidKeyStore provider要求：AndroidKeyStore AES-GCM随机IV密钥 `setRandomizedEncryptionRequired(true)` 禁止调用者提供IV，而A38使用 `cipher.init(ENCRYPT_MODE,key,new GCMParameterSpec(...))`，是高度可疑的实机启动阻塞点，**尚没有ADB堆栈证明这次一定发生**。

A39改实际生产AES-GCM record编码为 provider `cipher.init(ENCRYPT_MODE,key)` 自动生成IV再 `cipher.getIV()` 存入现有versioned record；不改变原密文认证AAD格式或decode。改自动保存为host实测 `RootStartCredentialSave.attempt` 的可选操作：本机加密保存失败绝不阻断原Service/Go启动，用户看到简短失败提示并得到固定 `UI_CREDENTIAL_SAVE_FAILED`。保留手动保存/清除。Activity新 `UI_OPENED`、`UI_START_TAPPED`、`UI_START_VALIDATION_REJECTED`、`UI_START_DISPATCH_REQUESTED`/DISPATCHED/FAILED及load事件，写入与Service相同的有界固定TXT，report最后会话以最近UI触摸或Service START为界，能真正区分本机输入没过、没真正触达Service、RootGo阶段。不得输出原密码、短Key、SNI或原生错误字符串到TXT。

同步Java/JVM真GCM随机IV/双密文解密/篡改拒绝、可选保存失败仍能继续Service的生产wrapper、诊断会话优先级，原Go TLS三态、Linux Normal/off Oracle和签名ARM64 APK同源重跑。Android手机没有在CI上进行直接Keystore设备执行；仅在用户下一次安装/点击后确认症状是否消失。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A39 A38实机0事件提示Service前UI入口可能拦截，修AndroidKeyStore GCM provider IV兼容并将凭据保存失败改非致命，增加UI启动前阶段收据与Host测试。"}
```
