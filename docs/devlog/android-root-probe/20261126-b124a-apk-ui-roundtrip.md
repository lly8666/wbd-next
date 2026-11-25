# B124a｜日常APK完整配置回归修复

B124 SOURCE `d162770c2582e093f97acc30fea33558776691b1` [Action 45655760338](https://github.com/lly8666/wbd-next/actions/runs/45655760338) 18 SUCCESS/4 FAIL/8 SKIPPED。七模式实际独立Android↔Linux原TLS、租约、M4普通App TCP/UDP、Stop与Normal自动重连均PASS；Fixed/Auto实际恢复交付及质量反馈PASS。最新ARM64实体和真实性能仍未验。四个失败分别为旧DNS状态按钮源码断言、API35/36第二次编辑密码控件找不到、BPF缺少测试ELF。无在途Action。

B124a只修重构APK：切页释放旧输入焦点并归位ScrollView，给现有输入框明确可访问名称；真实UI测试按可见输入框双向滚动查找，继续真实十槽完整保存、重启、删除、SAF导入/再导出。Java Properties.store自带时间注释，不能要求两次备份字节完全一致；解析真实WBPC/WBP2逐槽比对每一设置字段及实际密码/Key/CA字节（独立临时真实CA导入），不修改原备份格式。同步新DNS状态按钮的源码断言。B124全量marker含BPF任务，native构建也必须产出同SOURCE测试ELF；本次用既有B117/B115 marker定向重验普通业务/BPF与API35/36，不重跑七模式。

原Go/Rust、协议、MTU、DNS、B123 IPv4-only、共享、保存格式、TLS选项均不变，无新增防御门或热路径工作。功能卡旧快照已归档，main/M0 registry/cursor不改；PR36 Draft。新SOURCE验证待Actions。下一步只验实际APK与BPF，不增加功能矩阵。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Fix B124 UI focus and exact live backup roundtrip regression; align DNS label and BPF fixture build with existing functionality."}
```
