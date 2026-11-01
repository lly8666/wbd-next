# PLAN027 H713 — real 100/300ms original Windows/Linux kernel pulse was not a zero-loss wire

Recovered exact original signed Windows NPF/Wintun↔Linux WSL2 Go TLS/Rust run [41264542737](https://github.com/lly8666/wbd-next/actions/runs/41264542737) at frozen product SOURCE `6ece9eab653f46a716e8d3a0927fb74bec4819e8`, original prebuilt run41226521824, scenario SHA256 `75e2f6aa2e3f8909872390641233db8bc0a27db78908773697c798c9ce7ec63e`:
- Scenario true symmetric 100% kernel TC eth0/IFB pulses after 20s for 100ms and 40s for 300ms, actual **minimum simultaneous 100%-loss measured 103.973ms and 303.285ms**. Offered Windows9.9973/Linux10 Mbps each, first delivery Windows0.994154/Linux0.994462, first delivered9.9418/9.9443Mbps.
- Full 60s actual UDP/TCP/Stop summary had `PASS_BOTH_OWNED` with separate finally `WL_REAL_LINUX_OWNED_STOP_REQUEST_FAILED code=1` after test (cannot silently erase the differing finally exit). Kernel Linux TUN drop0/fq0, Windows NPF ingress delta0, source CPU Win3.4062s/74.625s ~4.564% one logical core, peak RSS42,041,344B.
- Original end-to-end **Action FAIL** and `WL_PUBLIC_REAL_MODE_RESULT normal FAIL`; its V2 measurement status was `MEASURED_BOTH_OS_KERNEL`, but shared `first_delivery_ok_for_scenario` treated base random `loss_pct:0` as 60s lossless and demanded first≥99.9%, ignoring explicitly measured full-loss pulses. Existing exact FAIL stays FAIL. This is not evidence of unmeasured p99, perfectly recovered TCP or guaranteed Stop after all possible aborts.

H713 changed ONLY `tools/m0_wl_perf_v2_config.py` / `tests/test_m0_wl_perf_v2_config.py`: under explicit `kernel_loss_bursts` require actual first fraction ≥1−(sum declared burst ms/1000)/measurement seconds−2 percentage points, both real receivers; ordinary no-loss ≥99.9% unchanged, >0 random damage unchanged. Original driver + tc proof and native Stop remain separate mandatory gates. H699 genuine 99.4% is within bounded pulse duty; 90% or zero business rejected. The authorized acceptance is scoped original business under real burst, NOT lossless test promotion. Reuse SOURCEd066 genuine existing binaries for one new representative burst Action if current cheap regression passes and exact manifests valid; no product source rebuild, no new impairment generation, and only one same-scene Action.

PLAN027 §0 remains PARTIAL: Windows GameFEC1M/Stop and B106 new TLS Actions already in flight, C burst still not current-source PASS, C physical NOT_RUN and missing B remain explicit.

```feature-impact
{"kind":"none","ids":[],"reason":"Only correct source-locked measured real kernel 100/300ms pulse acceptance oracle and targeted fixture; no product data plane, configuration, API, protocol or platform change."}
```
