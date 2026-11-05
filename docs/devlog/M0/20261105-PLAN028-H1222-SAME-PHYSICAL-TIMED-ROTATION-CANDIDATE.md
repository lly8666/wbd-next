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
