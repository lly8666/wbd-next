# PLAN028 H1222 — user-requested unchanged-physical scheduled lane rotation candidate

2026-11-05 new explicit user request after H1221 user-directed scoped closeout: implement timer-initiated cold lane replacement with network unchanged and sustained application traffic. Old H1221 `53c7d474` physical seven-mode source-specific PASS and Windows/Android/ICMP/CPU/H998 qualifications remain unchanged; this is a **new, still unverified** SOURCE delta.

- Original Linux client CLI adds `--rotation-interval` as a duration, disabled by default (0); opt-in 5s..24h. The 1460B complete outer IPv4 default is unchanged. Server cannot select a global timer that rotates unrelated clients.
- Same existing Linux original-Go TLS -> Rust M4 current/candidate/retiring owner supervisor is the **only** controller. Timer reads actual effective physical route/MTU without treating gateway/MTU-only OS notifications as NIC/IP change, then makes a distinct source port/real certificate+password TLS authenticated generation. Protected lease/identity, OS MTU readback and Rust M4 must be READY before old exact Stop; no FEC/record/AEAD/PN/wire changes or new Go steady pump. Failed candidate retains A and existing bounded 1–30s retry.
- New native x86/x86 build-once/workflow matrix has separate Normal Auto, Game2 Off, Game4 Fixed6 scene jobs on one shared443 server. Each scene maintains 3 independent authenticated devices, route/NIC/source/MTU unchanged, 3 simultaneous *real TUN UDP* streams during two timer rotations, original Go TLS/Rust native ready + old-generation Stop, genuine route/TUN/lease readback, received-only RTT p99 and process CPU ticks (not CPU causality). Same manifest-locked SOURCE binaries reused for all jobs.
- Baseline H1221 live same-connection 027A H998 FAIL, Android and remote ICMP NOT_RUN, Windows timer NOT_RUN, precise authentication→first packet and causal CPU NOT_MEASURED. ARM64 is next complete Linux task, not a mixed-QEMU exercise.
- Current status **SOURCE_CANDIDATE / NATIVE_NOT_RUN**. Do not advertise new functionality PASS until Actions and evidence artifacts are collected. Prior run41950047809 governance failures and run41950047660 G2 registry-revision failure were collected, not hidden or repurposed as product qualification.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"New user-authorized opt-in unchanged-physical timed original TLS/Rust replacement and three native business scene candidates; NOT_RUN pending exact SOURCE Actions."}
```

## 原生首轮与精度补强

- SOURCE `8a803303` native [Action41957225539](https://github.com/lly8666/wbd-next/actions/runs/41957225539): 1 build PASS, three native x86/x86 independent scenes PASS, initial client TLS epoch 1 then two timer-triggered protected epochs 2/3, old exact Stop 1/2, all 2265/2265 real UDP echoes, no physical NIC/source IPv4/MTU change. Per rotating lane received-only RTT p99: Normal Auto 0.621ms, Game2 Off 3.396ms, Game4 Fixed6 17.747ms. CPU process ticks captured but not causal.
- This follow-up narrows the proof: each generation's *actual authenticated lease* must match the concurrently responding address, and fixture exports real Go/Rust runtime logs and ready-detection→first echo metrics. The new fixture SOURCE is **NOT_RUN until its own new Action**; do not silently promote 8a803 results onto a different SHA.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1222 native three-mode 2265 real UDP verified at exact 8a803 source; strengthen current-source authenticated lease and timestamp proof without changing steady packet wire."}
```

## 证据增强脚本最窄修正（H1222）
- SOURCE 08e75d8 Action41958192998: native build PASS; three enhanced scene jobs stopped at generated Bash syntax check before executing, not a product FAIL or a new source PASS. Fix three source backslash escapes: true shell newline and one-level raw regex escaping.
- Move three full fixture `bash -n` preflights ahead of expensive original Go/Rust native compile; no product/MTU/wire change.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Evidence fixture backslash correction and early whole-scene syntax preflight; no new product changes, 08e75d8 results retained failed."}
```

## H1223｜增强原生 SOURCE 冻结结算（2026-11-05）

- [Action41958680473](https://github.com/lly8666/wbd-next/actions/runs/41958680473), SOURCE `ed80573fb3801e64814a2d38781c44ea8f3defac`: pinned original Go TLS/Rust M4 one native x86/x86 build; three parallel jobs Normal Auto, Game2 Off, Game4 Fixed6 all PASS, 12s periodic on unchanged real physical NIC/source IPv4/MTU; authentic [1,2,3] generations and exact Stop [1,2].
- Three concurrently authenticated clients produce genuine no-app-retry UDP throughout each timer handover: Auto 738/738 (rotating p99 0.734ms), Game2Off 761/761 (3.739ms), Game4Fixed6 768/768 (14.339ms); grand 2267/2267. Per-device authenticated lease readbacks match live UDP source and stay constant across all three generations; distinct client devices remain online.
- Second timer event→new authenticated READY poll observed: 163.656 / 885.227 / 842.608ms. READY observed→rotating device first genuine echoed UDP: 60.313 / 8.164 / 15.101ms. Includes 250ms poll cadence; NOT exact TLS auth completion→first wire packet, NOT a 200/500ms native network notification bound. Process CPU sampled in actual three-stream scene, causal CPU cost NOT_PROVEN.
- Evidence JSON: `docs/evidence/M0/PLAN028-H1223-SOURCEED805-X86-TIMED-SAME-PHYSICAL-THREE-MODES-REAL-UDP-PASS-20261105.json`. Each job artifact includes 4 original Go/Rust runtime logs, kernel route/TUN readbacks, CPU ticks, full receipt timings, zipped artifact SHA256. No new data-wire/FEC/recovery algorithm.
- This qualifies newly user-authorized Linux x86 timed three-mode UDP only. H1221 historic seven-mode real physical source closeout separate, H998 same-socket live MTU and historic ARM Game4 Action FAIL preserved. Windows timed, native ARM timed (next complete Linux task ARM64+ARM64), Android, remote ICMP, timed inner TCP, same-account two-device timed authentication, precise TLS-auth→first and CPU causality NOT_RUN/NOT_PROVEN.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1223 native x86 3-mode unchanged-network timer source-specific 2267/2267 UDP, lease and exact old Stop; old FAIL/NOT_RUN maintained."}
```
