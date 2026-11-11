# PLAN028 H1622 | Keep true H1621 pre-dispatch FAIL; print saved SHA without mutating source lock

Original H1621 wrapper [Action43109798583](https://github.com/lly8666/wbd-next/actions/runs/43109798583) overall FAIL in the *cheap wrapper preflight* before a Windows workflow was dispatched. Native business/105s idle NOT_RUN. Actual prefix assertions confirmed the exact immutable base 105s scenario differs only by new scenario ID and MTU 1400->1460; the original positive configured_native_test_mtu() for default1460/1460 and negative 1460/1400 both succeeded. Then Python raised `KeyError: 'scenario_sha256'` solely because the source-locked equality check popped this hash before a debug `print` attempted to access it. Original failure remains.

H1622 in the existing wrapper captures `native_scenario_sha=s.pop('scenario_sha256')` and prints saved `native_scenario_sha` after the exact entire dict equality check. No disabled assertion, no mock, no product/Go/Rust code, no rebuilt binaries. The clone still has original business 105s idle then 60s 10 Mbps each way, 25ms 0 loss, real original Go TLS/Rust and signed Windows Npcap/Wintun and WSL2 Linux. The original successful H1600 binary source8a Action43027983611 and original EXE/DLL/Go/Rust/ISA-L hashes are reused.

The new wrapper only triggers one native real Windows+Linux workflow when the check passes. A wrapper SUCCESS is never a business PASS; require the target's real original OS/kernel, TLS M4/UDP and final Stop receipt. Keep H1620 original 1400 mismatch Action43066195581 FAIL, H1621 wrapper FAIL and all previously successful Linux scoped network artifacts. No Windows L3/nearMTU/multiWintun rerun.

```feature-impact
{"kind":"none","reason":"Only logging saved scenario SHA after immutable source-lock validation, no product/GUI/default changes."}
```
