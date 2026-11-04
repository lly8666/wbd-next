# PLAN028 H1126 — exact Windows test source blob pin, no runtime code changes

[H1125 Action 41810122415](https://github.com/lly8666/wbd-next/actions/runs/41810122415), [41810122439](https://github.com/lly8666/wbd-next/actions/runs/41810122439) and [41810122472](https://github.com/lly8666/wbd-next/actions/runs/41810122472) remain **FAIL_PRE_ASSEMBLY**, not Windows native product failures: H1125 updated real Go product file result_blob, but the new negative-unit source m0_native_v4_reauth_windows_test.go was still manifest-pinned to b031bac4ec63caf4327b164b51f58ba2b3cabc3b instead of b1b0e2f88a8f63015102235026305e60602020c9. Correct that existing manifest operation only. Existing native scenario resumes via [plan028-win-physical-owned]; no extra matrix or new TLS/record logic.

Until true Windows network source4 change→new original TLS/Npcap/Wintun, first business, MTU readback and exact Stop pass on one source, the signed Windows cutover is NOT_QUALIFIED. Prior H998 online hot-MTU FAIL, ARM64 historic Game4FEC Action FAIL, remote ICMP and CPU causality gaps preserved.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct source-locked Go test blob in existing assembly manifest; no product or feature behavior change."}
```
