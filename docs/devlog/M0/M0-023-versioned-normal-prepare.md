# M0-023 — versioned private Go V4 owner Prepare is normal Rust code

CODE SOURCE `5aada1d5ada91fb13949a0bd6fbec2a7fb396576`; **PARTIAL_VERSIONED_NORMAL_BUILD_PREPARE_PASS**. Exact-source native Action [38870573492](https://github.com/lly8666/wbd-next/actions/runs/38870573492) attempt1 SUCCESS (build/consume); detailed artifact digests in [evidence](../evidence/M0/M0-023-versioned-normal-prepare.json).

Why now: the prior actual protected-Go-to-original-Rust raw/TUN path was driven by a TEST-ONLY FFI that built the Rust Prepare parameters itself. The ordinary Go admission code now freezes a versioned WBGH-v1 command containing the original SYN flow/MSS and actual PrepareTransition RX boundary. Existing cgo bridge merely conveys it, while **ordinary-built** `v4_protected_handoff` validates the command and constructs the existing M1 RX/TX plus M3 AEAD/PN owner as Prepared. Protected reply→Detach→exact Go SenderNext Commit is unchanged; no earlier Active, no public arbitrary cold install or standalone key attestation.

Exact SOURCE native verified both Go and Rust owner/preparation tests, new normal Rust malformed version/size/tuple/MSS cases, plus 3-suite real isolated Linux raw IPv4/TCP/TUN bilateral first application packets. Same SOURCE Governance and governance-maintenance SUCCESS; scope audit was SKIPPED, not PASS. Different-SOURCE previous ABI/cross/Go control greens remain historical references, not combined eligibility.

**Historic failure retained:** earlier SOURCE `9f248938` native run38870306754 FAILED because new negative test assumed an already-zero version high byte was invalid; this assertion was corrected by rejecting actual malformed fields in later code, not bypassed with seed changes.

Still **not product**: no non-test Rust C ABI session installer, production Go V4 runtime gate remains fail closed, features=0; held M4 driver stop B01–B04, actual external SYN, reconnect, veth netem, product Normal/off performance and physical/500Mbps NOT_RUN.

**One next action:** implement the non-test Go-verified private native control adapter to the same ordinary Rust Prepare/Commit transaction with real provenance and bounded Stop; do not advertise V4 until real B01–B04 and product gates pass.

## Governance recovery after H88

H88 SOURCE `b7ab36c3331a67d5bb9ab25af294599df9769d00` Governance [38871078627](https://github.com/lly8666/wbd-next/actions/runs/38871078627) **FAIL** solely on main `Central worker scope audit` metadata: cursor evidence expected `source_sha`, whereas this evidence carried the synonymous `code_source_sha` only. No Go/Rust/kernel test failed. Recovery S adds the required exact same CODE source field and preserves both the H88 failure and prior native PASS. Ordinary push Governance never means full tool selftest or product.
