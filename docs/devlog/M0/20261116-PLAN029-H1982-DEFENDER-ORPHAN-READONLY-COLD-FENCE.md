# PLAN029 H1982｜Defender 独立 owned sidecar 的中断恢复漏检

## 问题与原确证
- Normal CN Direct TCP 已采用四阶段 no-WFP WAL，并在实际 Applied 后生成一条 generation-bound 精确 Defender TCP Allow。规则身份的 `intent/owned/cleaning` 持久凭据在 `statePath+.plan029-defender-tcp`，不是旧五阶段 WFP guard。
- 原 `N4NativeInspectState` 只检两类路由 sidecar；原 `N4NativeRecoverState` 在无主 `.n4-owned-wal` 且只剩 Defender sidecar 时返回 nil，可能错误报告“网络干净”。下一代 `n4AssembleWindowsNoWFPNativeTxn` 没有拒绝这份旧代证据。实际是否存在对应的 Windows Defender Allow 此时未知；不能跨代删除。

## 本批代码（尚未实网）
- 只读状态增加 `defender_sidecar`（**仅磁盘存在**）、`orphan_defender_sidecar`。没有主 WAL 时 Recover 遇到侧证立即 `ErrN4JournalConflict` 并保留；不调用 COM、不删除/猜测规则、不开全局防火墙。
- 在新 no-WFP 四阶段 cold assembly 真实 Wintun/Apply 前加入 sidecar absence 检查；无凭据时不限制正常新世代，残留时拒绝 takeover。旧 v1 已有 WAL 的精确恢复完全不变。
- Windows Go 的三个纯磁盘回归检查状态不能误报 absent、Recover 不能假成功且原内容不变、下一代冷接线不能重用 sidecar，sidecar 删除后各自允许正常 absence；OS/规则实体及 native 网络 **NOT_RUN**。本 SOURCE 只等待原 push Actions 的编译/治理结果，不额外 dispatch。
- 不借本批替代 D5 真实崩溃恢复，也不替代 H1978 原 native FAIL、H1974 五次 61ms 尾延迟和 GUI/Game4/IPv6/P1–P2 等剩余 PLAN029 出口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1982 fail-closed read-only discovery of orphan exact owned Defender Allow sidecar across status, native recovery and next-generation no-WFP cold preflight; 3 pure file regressions, new source CI/native NOT_RUN."}
```
