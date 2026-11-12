# PLAN029 H1662｜Windows native DNS source-only verification and scope gate (2026-11-12)

- Frozen source `474eeb66e5f5048a6dd7afa78c863d8bc70e212c`, pinned Go donor `a7a82db31fe736ffedee330795a3234d358f1984`. Windows Action [43180302066](https://github.com/lly8666/wbd-next/actions/runs/43180302066) SUCCESS: actual manifest/Go Windows build + **4** `TestPlan029*` isolated tests PASS. Artifact 13926635142. **BUILD_ONLY, not signed L3, DNS or GUI business PASS.**
- CLI/server-ip domain wiring and one-shot NPF DNS A physical discovery; no DNS system loop in source design. Requires actual WFP/capture OS verification. IP literal never resolved. SNI and local pre-shared route-key unchanged. GUI field label now IPv4/域名 and outer MTU 1460 default, max 1500 explicit; actual WinForms OS readback still not qualified.
- New user §2A mandatory Windows V4 native Wintun post-capture CN/LAN/custom direct TCP/UDP return path is NOT_IMPLEMENTED/NOT_QUALIFIED; old Go route classifier and 2 /1 compact OS routes are not proof. No thousand route/WFP escapes.
- Startup flows padding unimplemented; no fake proof. Old 028 ACK, independent Windows L3 and human GUI signed setup remain exclusions.
- Retain source guard FAIL [43180104430](https://github.com/lly8666/wbd-next/actions/runs/43180104430) and feature catalog FAIL [43180104298](https://github.com/lly8666/wbd-next/actions/runs/43180104298); do not rerun noisy old 028 workflows. New devlog declares features and new governance validates this snapshot only.

```feature-impact
{"kind":"updated","ids":["client-domain-bootstrap","gui-config-feedback","dns-split-ipv6"],"reason":"PLAN029 H1661 scoped Windows Go DNS/CLI build proof with source-locked Action; record real-network/GUI and mandatory native CN split unqualified, preserve 028 scoped gaps."}
```
