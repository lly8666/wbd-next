# PLAN027 H519 — distinguish valid kernel/Stop measurement from actual outer recovery quality

H510 source1644 real 1/5/10/30% loss retained correct first/TC and Stop despite near-zero Windows R. The existing `m0_wl_outer_repair_verify.py` returned `PASS_SCOPED_WINDOWS_OUTER_REPAIR` for a **validly observed** zero-repair result; external reading could incorrectly promote it as true outer recovery PASS. H519 retains that exact scoped measurement result and all original F/R/C, true source and TC/Stop checks, but adds independent `repair_signal_grade`: `NO_OUTER_OPPORTUNITY_ON_MEASURED_LOSS`, `FALSE_REPAIR_ON_NO_LOSS` (>0.1% actual R/F despite no injected tc loss), `NONZERO_WINDOWS_REPAIR_NOT_BILATERAL_GRADE`, or `LOSSLESS_BELOW_ONE_PER_MILLE_NOT_BILATERAL_GRADE`. `product_repair_qualified` stays false, because only one Windows sender and not both original peers' app recovery and full damage matrix is measured by this gate. Deterministic unit covers zero true repair, no-loss false signal and positive measured signal.

Not a new performance threshold or repair quota. The status still verifies evidence integrity; additional grade is a truthful **diagnostic**, never a forged PASS or action failure to hide. H517 nonstarved Windows SACK TX and H516 fresh compiled binaries remain subject to original real native testing; no published F/R matrix yet.

```feature-impact
{"kind":"none","ids":[],"reason":"Extend existing real native outer repair measurement with separate honest diagnostic grade; no product semantics, arbitrary quota or public feature claim."}
```
