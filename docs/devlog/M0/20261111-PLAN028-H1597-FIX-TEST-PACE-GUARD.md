# H1597｜真实app范围纠正：0.6→0.7，不下调发生器安全门

H1596 source`496309022f2b1f9d39c1b2d7db80770a49321886`已派发单Wintun+Linux Bob同账号跨OS 150s Action`43024873684`，其治理`43024873618`、全体regression`43024873825` SUCCESS。但前置源码自审发现新环境变量`WBD_PLAN028_WIN_150S_SCALE=0.6`低于成熟原真实内核业务发生器`tools/m0_plan028_h1548_mixed_os_app.py`原有`0.65<=scale<=1.35`硬边界。原Action即使编译成功，在后段仍会因**测试夹具负载非法**失败。不能指责产品或删负载界限、不能在当前同类Action正在运行时再次派发。

本H1597将仅测试夹具接受范围`0.69..0.71`、原workflow H1596 marker测试专用速率`0.7`、原严格报告0.7断言和同一源级静态用例全部对齐。依旧低于已测4vCPU宿主1.0负载CPU92.6%，但保持有效的真实app pacing。原H1581 H1577配置/测试源及产品CLI默认不变。此提交有`[plan028-harness-offline-only]`，**绝不在第一场仍运行期间派发同一网络场景**；先收第一场原始失败结果，后续仅一次必要修复复验。用户排除同宿主多Wintun，H1587历史原FAIL继续显示。

```feature-impact
{"kind":"none","reason":"Only repairs a source-locked test-only pace value in original native OS fixture and same-scene workflow/tests, plus scope docs; no product behavior/default modified."}
```
