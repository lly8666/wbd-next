# 2026-10-23 recovered: actual product TUN pre-read loss and scoped fix

Recovered exact already-dispatched [39911913234](https://github.com/lly8666/wbd-next/actions/runs/39911913234) (artifact 12483556117, product 99042008e8f42f334ed635df92945e00e53c45dd). Business FAIL C2S 144/5884=2.4473%; S2C 153/5884=2.6003%. No duplicate dispatch.

First failing boundary in Rust original TX: the TUN read consumed valid inner IPv4 before Arena::allocate. Client UDP9498 staged9395 (lost103) plus TCP11349 staged11225 (lost124) totals **227**, exactly post-read arena_failed227. Server UDP9487 staged9374 lost113 plus TCP11393 staged11272 lost121 totals **234**, exactly arena_failed234. Peer RX LINK and TUN report zero malformed/discard/sink failure. All counts full session, not limited to steady cohort.

Root is a real 128-slot 2048B M1 source slab pool held across ~408ms authenticated RTT (206 records/s means ~84 network flight slots before 32-slot batch/feedback/repair). Fresh TUN admission was irreversible before a loan was secured. Logical 131072 shadow slots do not provide actual plaintext/ciphertext M1 backing.

Fix only source boundary and cheap bounded capacity: reserve owner slot BEFORE kernel TUN read; when no slot defer without consuming, yield 1ms if no other work and TUN stays level-ready. Unused reservation drops immediately on jumbo/invalid/empty. Normal/off public Linux feature7 pool 128 -> 512 existing bounded FEC-size (~1.1MiB/session), not a 500Mbps qualification. New pre_read_deferred distinguishes non-dropping backpressure from fatal legacy arena_failed. No quota/PTO/retry/crypto/MTU changes.

Native+MTU and real same-scenario measurement are pending at write time. Evidence JSON beside status; do not declare full business PASS until exact SOURCE Actions measured.
