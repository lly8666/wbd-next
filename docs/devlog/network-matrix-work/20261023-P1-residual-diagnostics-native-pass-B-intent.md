# 2026-10-23 read-only Normal residual diagnostics native PASS → one B-only observation

Native ARM64 Action39893574791 source21b1a9c PASS: product bundle12475394629 SHA256029af2ff..., new retirement-bucket unit PASS, adaptive timing unit PASS, prior Fixed M2 unit PASS and 9 MTU/DF/Stop PASS. No recovery behavior changed from source2a388; only one pre-Stop numeric FFI/CLI readback was added.

Run exactly one source21b1a9c Normal2pct 60s leg at the same seed/load/loss/delay. Read the actual learned SRTT/PTO/Tcache and classify every shadow retirement by repair attempts. This is deliberately not another A/B because the old/new timing causal effect was already established in Action39892580264. No configuration change is authorized from the diagnostic run itself; first remaining stage wins.