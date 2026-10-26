# 2026-10-23 P1 sparse-floor repair burst native PASS → one same-VM AB

Native Action 39895511143 SOURCE `dce9d23009b8803ac67484df9b6d0608b3641801` completed SUCCESS. Product artifact `12476119650`, SHA256 `711026721bab51faa2a91ecb71990ce5f2edfbb83242a7af86af66dd8b34fe79`; sparse-burst unit, adaptive RTT unit, retirement diagnostic unit, Fixed M2 unit, and existing nine MTU/DF/Stop cases all PASS.

Behavior delta from old diagnostic SOURCE `21b1a9c1001c93497376de9cd052e37d0d7f2aec`: local repair pacer instantaneous cap at 1500 MTU is now32KiB minimum rather than12KiB, but the same per-epoch `max(fresh/10,32KiB)` quota and pace rate remain. No timing/seed/retry count/auth/crypto/fresh queue changes.

Next is exactly one same-VM sequential AB on the prior failed Normal2%/200ms/60s point. The causal expectation is lower blocked and expired0; acceptance remains <=1% UDP residual both directions. No Fixed rerun, no H500 yet.
