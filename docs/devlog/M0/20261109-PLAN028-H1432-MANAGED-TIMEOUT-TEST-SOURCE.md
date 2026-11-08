# PLAN028 H1432 | Win/Lin L3 preflight-only old managed-timeout assertion

Action42507562916 and Action42507776166 both fail **before** signed Windows native job: the existing two files tests/test_m0_wl_native_os_deadline.py and tests/test_m0_plan027_managed_unilateral.py had separate literal `timeout-minutes: 24` oracles. The first was updated for conditional 52/24; the second historical managed test now likewise asserts exact conditional, maintaining ordinary 24m and requiring explicit `[plan028-win-linux-1800]` for 52m. No real product/Wintun/Go/Rust long network started, so no product fail or PASS. New subsequent Action must build original product and complete 1800s before promotion. No replay of unrelated native tests or ARM64 in-flight scenes.

```feature-impact
{"kind":"none","ids":[],"reason":"Only static CI timeout assertion for source-locked conditional Windows L3; no product or network runtime modification."}
```
