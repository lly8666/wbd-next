# Windows crash / upgrade recovery fix

User reports GUI cannot exit after original child failure, and existing no-WFP v2 WAL refuses recovery demanding live original owner. Separate fix branch from main while PLAN030 test completes. Stop releases dead child independently; GUI attempts native recovery before next connection and can exit with explicit unresolved status. Reuse existing v2 route receipts and native per-interface restore; no WFP guard required for v2. Real signed Wintun child test with actual four-stage receipts, a private TEST-NET /32 route, TerminateProcess and separate process native Recover; real WinForms close after stopped child and failed recovery. Existing Rust DLL and signed Wintun from exact unchanged 029 release. No physical user host mutation in this turn; qualification pending. Old script/v1 formats remain separate.

```feature-impact
{"kind":"updated","ids":["windows-network-wal","gui-config-feedback"],"reason":"进程退出和网络恢复解耦；当前v2持久状态复用已有原生恢复；真实WinForms和崩溃夹具待验。"}
```
