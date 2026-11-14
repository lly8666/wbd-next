# PLAN029 H1812｜D5 真GUI可见CN域名语义与三架构测试门禁

- H1811 SOURCE `b6e5797008fdf75d04fcca60af69e824894d15f6` 的 [三架构10k Rust Action43567463629](https://github.com/lly8666/wbd-next/actions/runs/43567463629) Windows x86、Linux x86、Linux ARM64，原始测试记录各 **10 passed / 0 failed**，两条 10k IP/domain 专项均 `ok`（Windows 域名冷建7ms/查询18ms，Linux x86 3/7ms，ARM64 4/10ms）。但脚本错把通过总数断言为 `2 passed`，实际 `#[path]` 同时执行生产模块原有8项，造成三个 job 同样假红；本批只修为“至少10项且两项D5具名测试通过”，不变业务代码。
- H1811 [真 Windows WinForms Action43567463580](https://github.com/lly8666/wbd-next/actions/runs/43567463580) **SUCCESS**：实际 WinForms 与当次原Go CLI/同源 Rust DLL 对 CN/all 模式切换、两个DNS、Direct额度、1460外层、Game4配置、非法额度拒绝、保存重开均有精确结果。此结果仍为配置/GUI，不是 Wintun networking。
- 新发现正式 GUI 原 pinned donor MainForm/fields 仍把 CN 模式描述为“只有中国 IPv4”，与目前已实网验证的域名/IP并集语义冲突。只在原 GUI 编译脚本中从固定 donor 源生成**只改两处文本**的派生 MainForm.cs+gui-fields.json（原文件不写），检查原字符串恰一次并记录派生SHA256/当次SOURCE；编译一次，GUI真实ComboBox/Hints直接反射验证“域名”“QNAME”，Go值不变。不动0号guard、账户、TLS、route模式枚举或保存格式。
- 当前 H1812 是实现待 CI 的 GUI 可见文案修复；D5 完整 GUI-origin 签名联网、P1/P2和Game4真实分流仍未完成，旧H1811门禁假红保留。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"Correct actual compiled Windows GUI CN split display to IP+domain union and QNAME single-resolver meaning using auditable immutable-donor-derived source; ensure same-source WinForms control readback."}
```
