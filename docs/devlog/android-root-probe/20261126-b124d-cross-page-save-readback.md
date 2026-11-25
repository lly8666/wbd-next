# B124d｜跨页保存真实槽读回，忽略无关治理红灯

B124c SOURCE `00d7d62f5a18ed874a1913d9679facb77967ef52` [Action 45710294156](https://github.com/lly8666/wbd-next/actions/runs/45710294156) 11 SUCCESS/2 FAIL/10 SKIPPED，签名ARM64 APK/接线及基础构建通过；[API35](https://github.com/lly8666/wbd-next/actions/runs/45710294156/artifacts/15068206197) / [API36](https://github.com/lly8666/wbd-next/actions/runs/45710294156/artifacts/15067552858) 两实际回执均 CA 导入、第一槽保存、CA清空、第二槽保存PASS，普通UID socket PASS（非WBD隧道性能）。两者同在设置页第二次保存槽2后找不到状态文本而失败；API35现场截图明确显示“已保存槽位2：GameDaily”、MTU1380、Health30。短底栏不符合原find_scrolled为点击控件设定的24px阈值。此红不是已证实产品缺陷，但剩余完整备份验收仍未执行。

B124d只改UI脚本：设置页实际点击保存后，故意将当前未保存MTU改1390，再从服务器槽载入并核验持久值（槽2=1380且Health30；槽10=1400），因此不以底栏提示为保存证据；删除后检查槽10实际为空，恢复后检查槽和真实WBPC全字段、密码/RouteKey/CA字节。保留其余真实操作及验收条件，不把未执行步骤判PASS。无生产源码/协议/数据面修改，不重跑已完成的七模式/BPF，仅现有B115 marker的stock UI。功能卡与121单测已通过，既有独立治理红不作为APK阻塞、不改M0。新SOURCE待CI；ARM64真机及性能仍未验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Replace cross-page footer text locator with actual saved slot reload and persisted settings readback; retain complete SAF roundtrip."}
```
