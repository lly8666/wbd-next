# PLAN027 H502 — A4 intentional-loss oracle correction, not Stop defect

Original H499 signed native [Auto240 Action41029388055](https://github.com/lly8666/wbd-next/actions/runs/41029388055) child exited **rc0** with original `PASS_ACTUAL_WINDOWS_LINUX_NATIVE_auto`, native `stop=PASS_BOTH_OWNED` and server `V4_PUBLIC_NATIVE_STOP_DRAINED`; actual Linux first0.997028/Windows first1.0 across 0→5/15/30→0% genuine tc. Parent `tools/m0_wl_public_modes_e2e.py` applied the **no-loss >=.999** gate despite this intentionally lossy A4, so outer Action correctly remains historically FAIL but its root was a **wrong test threshold**, not a product Stop failure. The warning `WL_REAL_LINUX_OWNED_STOP_REQUEST_FAILED code=1` is a Python `finally` SECOND kill after the server already stopped, not the original owned Stop result.

H502 narrow oracle: exact A4 scenario, five real distinct ordered kernel stages, positive genuine first both ways and native owned Stop PASS. No weakening for any other zero-loss scene or outer repair. Original Linux Auto valid sampled revision6/profile0 and Windows readback revision4/profile2 are retained, but full 120s bilateral downgrade and true lifecycle B require separate source-true verification. H501 product source `0b7391a182f05947419c1211f01058b4798370a3` one native off30 build run41032003068 in flight; H499 Game2/4 runs41029390768/41029393488 in flight; no duplicate test.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Correct actual original A4 Stop PASS and false no-loss staged wrapper failure, preserve historical Action FAIL and full 120s grade open."}
```
