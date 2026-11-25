# B124c｜证书编辑器固定视口与完整配置真实模拟器验收

B124b SOURCE `f5a3c9e3113f881a70550b720cfc3de3bc9c526f` [Action 45664009603](https://github.com/lly8666/wbd-next/actions/runs/45664009603) 11 SUCCESS/2 FAIL/10 SKIPPED。签名ARM64 APK、原Go/Rust接线、完整WBPC Java编解码、基础UI及普通UID socket fixture PASS。API35/36均CA真实导入读回、第一槽保存通过；第二服务器字段编辑后在“清空证书”按钮定位失败。实际失败截图（[API35 artifact](https://github.com/lly8666/wbd-next/actions/runs/45664009603/artifacts/15047491433)、[API36 artifact](https://github.com/lly8666/wbd-next/actions/runs/45664009603/artifacts/15047231703)）显示多行PEM占满整个ScrollView视口，原实现仅setMinLines(3)。

B124c：CA导入/清空按钮移至编辑器上方；编辑器固定120dp、顶部对齐、垂直滚动，内部拖动不被父ScrollView抢占，外部留白正常翻页。完整文本、SAF、Keystore、原TLS及保存格式不变。UI自动化从卡片留白滑动；实际CA清空读回、再次载入不同槽CA读回，并增加逐槽已知设置值核验（peer/SNI/account/mode/DNS/MTU/Health），仍逐槽比较所有字段及密码/RouteKey/CA实际字节。未绕过按钮或真实SAF。

仅实验分支单提交，已有B115 marker触发真实API35/36 stock emulator，不重复跑已完成的Normal/BPF/七模式guest。原Go/Rust/MTU/DNS/IPv4-only、性能热路径及用户TLS选择均无变更。新SOURCE构建与完整UI结果待验，ARM64实体及性能未验。无main/M0写入。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Bound the actual CA editor viewport and verify clear, per-slot settings and full portable backup in real stock Android UI."}
```
