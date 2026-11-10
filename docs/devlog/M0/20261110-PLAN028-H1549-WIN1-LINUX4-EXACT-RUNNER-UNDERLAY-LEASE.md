# PLAN028 H1549｜恢复混合 Win1+Linux4 真实压测，修正管理物理路由来源限定

- User accepted scope: **one signed Windows original Wintun Alice + four genuine WSL2 Linux namespaces Bob Auto/Carol Game2/Dave Game4/Erin Fixed6**, one Linux Go/Rust shared TLS443 server, 200ms netem each direction, loss0/loss30 separate Runner each 600s, real full outer both directions target250–300 Mbps, true TCP+UDP, authenticated M4 and exact six Stop. Historic 5 Windows same-OS WFP global-route owner NOT REQUIRED, no fallback to unsupported bypass.
- Original [Action42852209993](https://github.com/lly8666/wbd-next/actions/runs/42852209993) source `7370d2bc`: cheap + Linux/Windows Go/Rust genuine builds PASS; both native jobs loss0 `129958228890` and loss30 `129958228970` failed **before original TLS/client/app** at `tools/m0_wl_gamefec_management_route.ps1:16` `MANAGEMENT_ROUTE_SCOPE_REFUSED`. This is pre-native harness-scope FAIL; business/runtime bandwidth `NOT_RUN`, no invented Mbps. Exact WSL Hyper-V+guest MAC cleanup ran.
- Old runner-management PS1 allows only GameFEC/Normal105 special or old two-client L3, while H1548 deliberately uses `WBD_PLAN028_MIXED_SCENE=loss0/loss30`, `WBD_WL_RUNNER_MGMT_PIN=1`, Normal one-Wintun, default1460, no five-Windows GUI escape. Add **one exact $mixedWin1Linux4 owner branch**, gated by those values and a unique `h1549-mixed-management-route-lease.json`; parent workflow selects same receipt in Arm and finally Restore. Existing GitHub owner RUN_ID:RUN_ATTEMPT+source, real Runner.Worker/Listener IPv4/32 only, unambiguous physical underlay, reject foreign preexisting routes, WAL exact removal, and no management-capture switch retained. No protocol/Go/Rust or global WFP route guard change.
- Added explicit PS1 contract to legacy H888 and new H1548 mixed tests. One native-public-two-os job preserved, and new commit contains the original scene trigger token for exactly the loss0+loss30 independent Windows runners. Do not duplicate if current Action already running.
- **Unrelated governance:** source7370/faa triggered separate historical frozen-manifest checks (old 54 operations expected, actual55) and feature gate; do not classify as mixed native product failure. Preserve first line and fix separately only after scope is unblocked.
- No start of PLAN029/030; PLAN028 `IN_PROGRESS`.

```feature-impact
{"kind":"none","reason":"Scoped CI-only management runner route lease authorization for exactly one signed Windows plus four Linux original-client 600s scenes; no user-facing feature or product protocol/Rust/Go change, retain all foreign-route protections."}
```

### H1550 治理 SOURCE 证据引用修正（不触发新 Windows 网络运行）

`tools/governance.py` 对 `.governance/workstreams/M0/cursor.json` 的每个 `evidence_refs` 约束是**该证据顶层 `source_sha` 必须等于 `last_tested_source`**。H1549 文件没有顶层键，旧 H1547/H1545 原源 `ed965f2d` 被误包含在当前 `7370d2bc` 引用里，会先于其它治理检查触发 `evidence is for a different SOURCE`。本次只补 H1549 的源 SHA `7370d2bc`，收窄当前 `evidence_refs` 至 H1548 和 H1549 同一来源；历史 Linux/ARM64 原证据仍留仓库，不改任何测试成绩、业务协议或性能场景。新 H1549 native Action 已经运行，本次文档提交没有 H1548 场景触发 token。
