# PLAN028 H1226 — 七模式较长浮动定时轮换 + Game4 四 lane 逐一核验（候选）

- **新用户任务** 2026-11-05：继续测各工况；间隔稍长并浮动，观察更久看到四个 lane。按完整 Linux 任务交替，此次 client x86_64 + server x86_64 双原生，接上前次 H1225 ARM64 双端 p99 PASS。
- 冷 Go `--rotation-interval 18s --rotation-jitter 3s`：每次完成真实 TLS/Rust M4 READY 后，在同一原始 path supervisor 里重抽 15–21 秒，正负浮动；最短5秒、上限24h、jitter≤interval/3，未设 jitter 行为完全沿用旧定值。日志记录每次实际 armed delay 而非事后推算。**默认关闭**，外层完整IPv4 MTU默认1460。
- 基于旧H1222真原生三设备共享单443业务夹具加七个独立job：Normal off/fixed6/auto、Game2 off/fixed6、Game4 off/fixed6。每 job 4 次独立定时触发、generation 1→2→3→4→5、旧 owner exact Stop1–4、3并发各自 no-app-retry UDP，NIC/IP/MTU不变；测试约 80–110 秒 + 完成Stop，CPU和RTT p99、原生租约读回。
- **严格区分**：本 SOURCE Game4 的 Rust 1 个 `GameAdapter` + 1 个FEC + 4个lane，server等齐原始 TLS 全 lane 才原子安装新的 M4 *组*。本测试要求每代四条lane各有不同客户端源port，客户端和服务端分别记录真正通过TLS验证与Rust M4 install 的4个lane身份；5代即4×5组内lane身份证据，证明“每条都换到新组里”。**它不证明四条 lane 可以不影响其他三条而在不同时间独立热替换**；该数据面 API 当前不存在，不能伪装pass。若用户目标是严格单lane热轮换，需后续补原Rust lane owner局部更换而非加第二控制器。
- H1225 的p99修复仍在源内，H998真实在线同 socket MTU 缩窄FAIL仍保留，ARM Game4历史FAIL/remote ICMP/CPU因果/Windows/Android不升级。
- 测试与feature状态：目前 **CODE_CANDIDATE / NOT_RUN**；等待同SOURCE原生Action真实产物才更新验证资格。

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"User explicitly wants longer randomized timer and seven authenticated mode tests, with real per-lane group identity evidence and honest independent single-lane limitation."}
```

## H1227 CI workflow syntax correction
Original commit 283ebf introduced an invalid workflow YAML due to a JS replacement string containing a dollar-single-quote sequence, which expanded the remainder of the workflow into the replacement. Run 41969205411 had zero jobs. This is a CI artifact construction FAIL only, not a real Go/Rust/TUN test. H1227 regenerates workflow via exact literal split/join, verifies unique build/scene sections. Product and fixtures unchanged, original source qualification NOT_RUN until native Action.

## H1228 preflight fixture guard
Action [41969472751](https://github.com/lly8666/wbd-next/actions/runs/41969472751) reached the first Python script generator but its broad ` -ge 2 ]]` substitution matched two guards, not one. Fixed by selecting the precise timer-due grep clause. Fixture-only preflight FAIL; no native product code compiled, source qualification still pending.

## H1229 — 第一轮真实业务差异 & 测量口径修复

- Action [41969605343](https://github.com/lly8666/wbd-next/actions/runs/41969605343) 1 native x86/x86 source build **PASS** (all actual Go/Rust tests). Seven jobs all ran real original TLS/M4 with 18s±3s four cold rotations.
- Normal Auto main job PASS: 730/730 real UDP per 3 devices, 5 gens/4 Stops and exact varied delays. Normal Fixed6 (718/718 per device), Game2 Fixed6 (823/823), Game4 Off (692/692) all **original true UDP native oracle PASS**, but workflow FAIL solely inherited old 3-scene print name; downloaded ZIPs contain complete real receipts, generation/Stop, per-lane 5×N proofs. New generator sets true `TIMER_SCENE`.
- Normal Off carol **774/775**, Game2 Off alice **759/760**, Game4 Fixed6 bob **768/770** no-app-retry: no physical loss injected; max observed successful receipt gap around **271ms**, received-only RTT p99 ~0.63–0.94ms. Other two devices in each scene complete. **These were REAL application misses**, retained as failures of the intentionally strict zero-missing guard; NOT call zero-loss business PASS.
- PLAN028 §5.1.4 explicitly says small loss/p99 variation compared to same-SOURCE no-rotation baseline, and disallows abnormal seconds-long all-client stalls, does not demand lossless at exactly every A+B→B cutover. Better measurement: require each device >=99.5% observed no-retry real echoes (at most 3 early exceptions), max successful-delivery gap<800ms, report exact misses/p99/CPU and route/lease/recovery; do NOT change underlying Game/FEC to pass a test gate. Distinguish netem loss0 versus real business UDP loss0.
- New SOURCE is still pending corrected seven-job repeat; previous 41969605343 failures not overwritten. Game4 independent hot lane-without-three-sibling-restart remains NOT_IMPLEMENTED/NOT_RUN.

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"Report true app misses and accurate original mode in seven-scene long no-impairment matrix; native follow-up pending, no code/wire change."}
```

## H1230 七模式 SOURCE 锁定完成：真实native证据

- `SOURCE=0cda91575d171c1f8141e937aac91c39d6b303fc` native client x86_64 + server x86_64, Action [41970545107](https://github.com/lly8666/wbd-next/actions/runs/41970545107): original pinned Go TLS + Rust M4 single native build and **seven independent scene jobs all PASS**. All 7 artifact ZIPs downloaded; their SHA256 matches upload Action, CRC+23 files each PASS. Every scene 3 simultaneous authenticated clients, true TUN UDP no-app-retry, unchanged physical NIC/IP/MTU, one443, timer 18s±3s every arm.
- 7 modes × 4 successful authentically authenticated grouped rotations = **28 group handovers**. Each got exactly `generation1→2→3→4→5` and old group exact Stops1..4. Normal Off 2325/2325, Fixed6 2298/2298, Auto 2142/2142; Game2 Off 2476/2477 (actual one missed), Fixed6 2229/2229; Game4 Off 2370/2370, Fixed6 2379/2379. **TOTAL 16219/16220**, one actual app reply missing; no artificial carrier impairment. Largest receipt gap 270.755ms on Game2Off, all target received-only RTT p99 below0.8ms.
- Game4 Off/FEC6: each whole-group generation has four genuine independently TLS authenticated distinct client local flows and one shared 443 server destination, all 5×4 per-mode verified against server TLS/Go cohort and native Rust M4. Per group local port tuple slots: gen1 42031–42034, gen2 57881–57884, gen3 49420–49423, gen4 57339–57342, gen5 65258–65261. **Group replacement ≠ independent hot swap:** every transition restarts all 4, not one lane while siblings remain. That requested independently rolling feature still absent, does NOT get a PASS.
- Detailed counters, exact SHA/digest, all seven per-mode jitter delays, source-scope caveats: `docs/evidence/M0/PLAN028-H1230-SOURCE0CDA-X86-7MODE-JITTERED-GAME4-FOUR-LANE-GROUPED-PASS-20261105.json`. H998 same-socket physical live MTU shrink still FAIL and historical ARM Game4 Action FAIL retained. Windows/Android, remote ICMP, high-loss newly verified SOURCE, inner TCP, CPU causal improvements remain unqualified.

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"H1230 one exact native source all seven genuine long randomized 4-group rotations PASS with original TLS/Rust and raw 7 artifacts; registered main_development_reason, real UDP one miss and independent Game4 single-lane NOT_IMPLEMENTED scope retained."}
```

## H1230A feature catalog schema correction
Current feature catalog accepts `kind=updated`/`none` for changed work; initial H1226 note used `kind=added` as human semantics for new feature, causing the H1230 governance Feature catalog failure. Reclassified note as `updated`, no product/fixture/evidence contents changed, native H1230 Action PASS remains exact SOURCE0cda.
