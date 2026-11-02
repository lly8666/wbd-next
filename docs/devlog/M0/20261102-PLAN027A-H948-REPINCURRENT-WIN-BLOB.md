# PLAN027A H948｜当前Windows Go overlay绑定精确blob

源 `7f84df245baf1f9924193dec8da5a38f22ae984f` 的H947 governance维护/主门均PASS，`tools/m0_wl_native_mtu_contract.py`单测已PASS。自动Windows-Linux Action `41452393607` 仍FAIL于 `python tools/prepare_windows_wiring.py --check-only`：`r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go` 的真实Git blob现为 `204fed35bc5919795b498e0d786796845abfdd90`，唯一调用它的当前 `manifest-plan020-m0.json` 还钉旧 `0af346548...`。另一个普通 `manifest.json` 不引用该path，故不需改它。此为原封装check正确拒绝的source不一致，不是产品网络失败。

本批只更新 `manifest-plan020-m0.json` 该文件 `result_blob` 字段；老Go原始 SHA、M4冻结历史blob不改、不重复构建无关模式。H946/H947未有真实Windows数值OS读回网络验证，相关状态仍NOT_RUN。

```feature-impact
{"kind":"none","reason":"Only current source-locked assembly manifest repin to already changed Windows Go product blob and cursor/evidence recovery; no additional behavior or public configuration change."}
```
