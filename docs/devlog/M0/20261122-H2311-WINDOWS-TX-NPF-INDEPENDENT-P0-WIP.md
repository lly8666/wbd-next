# M0/PLAN029 H2311 · P0 Windows TX/NPF split — WIP (2026-11-22)

## Scope and source

User authorized staged PLAN029 optimization: zero loss first, FEC OFF bounded one-shot repair at 1% then 5%, then fixed maximum FEC. **This checkpoint is P0 only**. Reused Draft PR [#68](https://github.com/lly8666/wbd-next/pull/68), branch `experiment/m0-029-throughput-arm-fair`; tested source `95a893d3b82bf6c8fc4b0f8a1c8019a017a7b922`. No production default, Go TLS, wire, ARM, or driver lease change. Not integrated in main.

## Implemented

- H2292 [original paired two triplets](https://github.com/lly8666/wbd-next/actions/runs/44951274107) proved combined Rust TX8/NPF16KiB → TX16/NPF64KiB goodput +48.7%/+21.4% with lower Win CPU/GiB, but **cannot distinguish these two changed variables**; H2290 Windows process kernel fraction ~82% does not prove which NPF call dominates.
- Retained `h2291_windows_tx_service` combined opt-in, and unmodified release default TX8/NPF16KiB. Added independent compile-time flags `h2311_windows_tx16_only` (Rust ingress16, NPF8/16KiB) and `h2311_windows_npf64_only` (Rust ingress8, NPF16/64KiB), **both off by default**.
- Experimental `h2311_windows_npf_trace` tracks sole TX-owner sendqueue calls/frames/submitted bytes/driver copied bytes/short copies, and direct `pcap_sendpacket` calls/accepted frames. Emitted only on native owner Drop/Stop, `PLAN029_H2311_NPF_STOP_PROFILE`. Driver-returned copied bytes are **not peer TCP receipt**; no per-packet Go FFI, thread, timer, synthetic traffic, or changed NPF copied-prefix handling.
- Reused original NPF accepted-prefix tests, H2291 source tests; added `.github/workflows/qa-h2311-windows-npf-factor-unit.yml`: one cheap Ubuntu source/fixture gate and one real Windows2025 native Rust mocked-driver test/compile. No Tailscale, WSL, signed-driver install, or WAN traffic in this checkpoint.

## Source-locked observations

- [First H2311 run 45026086892](https://github.com/lly8666/wbd-next/actions/runs/45026086892): static FAIL because inherited H2291 Python test required `h2291_windows_tx_service` to be the only NPF queue feature; Windows native SKIPPED. Test assertion updated for the new explicitly independent trial, no business claim from that red.
- [Corrected H2311 run 45026145314](https://github.com/lly8666/wbd-next/actions/runs/45026145314) SOURCE `95a893d3b82bf6c8fc4b0f8a1c8019a017a7b922`: **static SUCCESS, genuine Windows2025 native SUCCESS**. Python source contract; NPF mock prefix/copy tests and Win engine compilation for both flags under original feature base. This is a source/compile and native mock unit PASS, **not** a real WBD throughput result. Earlier H2292 true original product still belongs only to its frozen compiled DLLs. Historical push green with native skipped is NOT_RUN.

## Next specific P0 action (NOT_RUN)

Reuse `qa-h2292-true-windows-rust-aba.yml`, `tools/m0_h2292_true_product_ab.py`, `tools/m0_h2286_full_windows_product.py`, H2290 hotpath CPU sampler and H2276 isolated three-runner fixture. Permit new feature manifests only with same compiled source SHA and unchanged original Go EXE, including baseline rebuilt from that same SHA; never compare old archived baseline to new candidate while claiming source lock. Run same 4×25s real TCP+160 tiny echo and owned Stop, one qualified triplet then independent second when supported: A TX8/NPF16K → B TX8/NPF64K → A′ and, separately, A TX8/NPF64K → B TX16/NPF64K → A′. Record actual queue_call/driver copied-prefix, Wintun/TUN source and remote unique bytes, Win/ARM CPU/GiB, P99 and Windows sender TCP kernel state; exclude DERP and failing physical qualification.

**Verdict**: P0 code isolation and Windows native mock tests PASS_SCOPED; real Windows-ARM benchmark **NOT_RUN**; causal speed/CPU uplift **NOT_PROVEN**; default unchanged. P1/P2 not started.
