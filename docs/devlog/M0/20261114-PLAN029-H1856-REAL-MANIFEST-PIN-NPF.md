# PLAN029 H1856｜修正被实际读取的固定原Go装配清单

- H1855 [Action43611429748](https://github.com/lly8666/wbd-next/actions/runs/43611429748) Cheap job到`prepare_windows_wiring.py --check-only`失败：`assembly blob mismatch: r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go`。Windows编译/Wintun/真实P2 **NOT_RUN**，不能归因于Npcap修复本身。
- 追到`tools/prepare_windows_wiring.py:16` 的**真正**`MANIFEST=r0/go_overlay/assembly/manifest-plan020-m0.json`；H1854之前仅更新`manifest.json`，未被该执行入口使用。H1856只同步真正清单中两项原Go Npcap捕获handoff/Windows单测的确定git blob（`9511ced3926d`/`770a8845ee6f`）。不改donor、Go/Npcap源码和其余哈希，保留失败与原清单逐项完整性。
- 同时保留H1855已通过的治理/feature、准确cursor SOURCE；本commit才触发**一个**有意义的新SOURCE签名Normal P2。提交时真实P2 NOT_RUN，不改变028限定范围。

```feature-impact
{"kind":"none","ids":[],"reason":"Update exactly the two Npcap handoff Git blob pins in the manifest-plan020-m0.json actually consumed by original Go assembly; no product code or rule changes."}
```
