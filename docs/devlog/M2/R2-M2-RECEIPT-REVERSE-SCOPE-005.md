# R2-M2-RECEIPT-REVERSE-SCOPE-005 · bounded pure route admission

## Authority / handoff
Main registry (2026-10-15 wave3) active M2 revision2 epoch1, task R2-M2-RECEIPT-REVERSE-SCOPE-005, M2 worker branch work/m2-r2-recovery. Previous checkpoint evidence S5c652c2, H43c0e985 only cursor, H Governance38669865546 SUCCESS and native source06fe27a 33/33; CLEAN. Decision is main-only `docs/decisions/M0-parallel-worker-atoms-2026-10-15-wave3.md`; never add absent main-only path into worker cursor context_refs.

## Bounded implementation
- In recovery receipt state, `ReceiptRouteScope` represents an independently pinned (M0-trusted) outbound LaneKey and direction, reverse authenticated LaneKey, nonzero logical 16B tunnel_epoch, and explicit outbound DATA PN / inbound control record PN intervals. `ReceiptOpenFacts` contains M0-supplied post-AEAD+PN replay verified reverse lane/direction/epoch/control PN; **plain fields do not authenticate anything** and must never be constructed from untrusted wire alone.
- `ScopedAuthenticatedReceipt::checked_after_open` checks the reverse direction is the *opposite* of outbound, both lane generations/tunnel, logical epoch, control PN and every positive bitmap DATA PN before creating its private parsed AuthenticatedReceipt. Wrong/forward/stale scope is `DataError::Stale`; malformed policy/bitmap fails closed. It does NOT mint a cryptographic session/authentication constructor; source of trusted facts is M0's real authenticated session.
- `GlobalRepairAllocator::bind_receipt_route` pins one scope per registered logical direction before grants and denies epoch/rotation overwrite. M0 must retire and re-register the old TunnelKey on session/generation rotation. The new `observe_scoped_receipt` only admits an exact pinned scope plus matching owner shadow before applying *real* positive receipt data; `complete_scoped_batch` validates up to 32 ordered global reservations against each pinned client/direction/lane/record PN before any accepted/uncertain/definitely-not-sent accounting, with a fixed stack array. Original generic APIs remain available for old unit/internal owner integrations; M0 must wire new strict entrypoints, not call unscoped APIs with untrusted incoming facts.
- Existing process max cap, original-epoch definite NotSent refunds, conservative Uncertain debit, stale ID rejection, duplicate callback idempotence, frozen original ciphertext, fresh no HOL unchanged. No kernel syscall/socket, platform dependency, global lock, root Cargo or shared checker edits.

## New deterministic tests
Five new `r2_scope_*` fake MonoNs tests: wrong/forward lane, stale epoch/generation/control PN and bitmap data PN; positive ACK before grant, duplicate ACK and no fresh HOL; two tunnels both directions cross-scope atomic failure then mixed accepted-prefix+one uncertain+proven NotSent suffix; old epoch NotSent refund with Uncertain and departing/rotated tunnel; bounded 32/33 and unbound late batch fail closed. All previous 33 `r2_` tests retained, expect 38. Test qualification only via source-exact compiled-once GitHub worker-native Actions; historic G2/static and Governance separate.

## Nonclaims
This is a pure validation contract. A caller could lie when filling the public facts; there is NO cryptographic attestation or trusted Go V4 exporter implemented by M2. M0 must independently bind the legacy authenticated Go cold-session to exact lane+direction+epoch+PN after AEAD/replay, wire strict scoped receipt and driver results into the engine, and qualify actual product. Go V4/live AF_PACKET/native Windows/ARM, 500Mbps/p99, performance and physical remain NOT_RUN. Not a user-facing setting: no CLI/GUI/config changes.

## Exact code SOURCE native qualification and historical Governance

- Code SOURCE [6f19c7d](https://github.com/lly8666/wbd-next/commit/6f19c7d6e6d14c755e3eb657845a8d47718c8f71), worker-native [38674780276](https://github.com/lly8666/wbd-next/actions/runs/38674780276) attempt1 **SUCCESS**: compiled once, reused binary, `r2_` 38/38 (previous33 + new5). Build job116225786735 and consume job116225881366. SHA256 binary `47e7831f5f410e529d668ba2f6166b50d60a835017e89cdae8918c18939bad23`, log `c3c8131f548e23e6f4f8ad70a884486830d606d686f96332f8193beb561321e9`. Build artifact11945666570 digest sha256:8f4042e266362aafd1275c869c75e055d3b0c1835006bc1999bcaa000a9eeede, test result artifact11945404412 digest sha256:a6102979d2353cfc8777069164c101a43cafa222902c6041f096c470c29c88ab.
- Same code SOURCE G2 [38674780139](https://github.com/lly8666/wbd-next/actions/runs/38674780139) **SUCCESS**, separate build job116225786152/consume116225930164, result artifact11945706527 digest sha256:8071ac48482c369ae24535a6fe9f04fdf1c4acc4bc0006bae4e3245be795bc59 (historic bootstrap only).
- Same code SOURCE R0 static [38674780180](https://github.com/lly8666/wbd-next/actions/runs/38674780180) **SUCCESS**, job116225786126, artifact11944719856 digest sha256:93d8ced18204e1bc2ad57cf812619118360a7593765925735c3403bd43930590.
- Same code SOURCE Governance [38674780251](https://github.com/lly8666/wbd-next/actions/runs/38674780251) attempt1 **FAIL** job116225786513 `ROLE_SCOPE_FAILED: control or source moved mid-audit` during M0 concurrent main control update; preserves actual failure, **not** a source/Rust failure and **not** relabeled PASS. Artifact11945389517 digest sha256:bedb8099860778610d114f12d80c8dc2232d05f3cbcf51fc302c400a1f01c60f. Will use fresh evidence-S Governance and cursor-only H Governance; no repeated run-attempt retries without changed facts.

New test names:
- `r2_scope_forward_stale_epoch_rotation_and_pn_fail_before_receipt`
- `r2_scope_ack_before_grant_and_old_report_never_forged`
- `r2_scope_four_clients_directions_mixed_batch_rejects_cross_scope`
- `r2_scope_epoch_rollover_departure_old_notsent_and_uncertain_debit`
- `r2_scope_32_33_bounded_registration_and_old_callback_fail_closed`

Old receipt tests include duplicate/late/out-of-order report serial handling and positive bit release once; old R2 batch tests cover 0/1/32/33 normal results. This atom adds scoped denial, not live crypto/driver or real peer delivery.
