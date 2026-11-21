# UI 自定义 CN CIDR 编译冲突复核（2026-11-16）

- SOURCE `3ca59ead1a91a3e964c690931b2cf75fbc331d46` [KSU Action43897451393](https://github.com/lly8666/wbd-next/actions/runs/43897451393) **FAIL**，第一步 Java `build-app.sh` 失败：`SplitSettingsActivity.java:86 variable v is already defined in method build()`，随后 Native/KSU/真实UI均未运行；原成功 SOURCE `38fc188f35b9b15540222c41e2245b69344a093d` 的隔离UID路由PASS证据不受影响。
- 修复只把新增for-loop的 `String v` 改成 `String cidr`，保留 config JSON 原变量 `JSONObject v` 和已编译模块逻辑。继续以新SOURCE整条 App→Root→UI保存证据为验收，不把编译失败改称运行失败。

```feature-impact
{"kind":"none","ids":[],"reason":"Rename shadowing Java local in split-settings CIDR persistence after historical source-locked GUI compile FAIL; no product semantics change."}
```
