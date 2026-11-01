# H815 — H814 normal outer GameFEC genuine Windows NPF retransmit PASS, no throughput optimization

User clarified: **make the GameFEC cosmetic outer retransmission actually work with Normal-mode retransmission settings first; optimize CPU/architecture later**. All other PLAN027 remains paused.

H813 actual old source `89b373bfde0f3817651601920a95a57bc7b65c15` [native Action41335510708](https://github.com/lly8666/wbd-next/actions/runs/41335510708) was SUCCESS for genuine Game2FEC6 kernel UDP/TCP and Stop but **FAIL cosmetic Windows outer**: downloaded ZIP13095815466 showed `WBD_GAME_FEC_NORMAL_OUTER_STOP copied_appearance=0`, two lanes `sampled_original=[263,263]`, both shadow expiry263/none nominated; Linux cosmetic outer76. Core cause Windows H811 1/16 immutable receipts with `opportunistic_v3` GAP_ONLY scheduling could not obtain an exact sampled ACK head, and no PTO would nominate the cache before expiry.

H814 product fix [`96a2acd0b4ed`](https://github.com/lly8666/wbd-next/commit/96a2acd0b4ed0ee1b22d4836d205f1379bad6e59) applied Normal's bounded 1536 full original freeze/ACK index, existing 810ms nominal self-clocked adaptive PTO and 1200ms finite cache floor when no usable ACK gap; shared Normal global M2 grants (7MB epoch / 256 reservations / 524288 pending bytes), unchanged 80ms per-lane cap and **one immutable original ciphertext/PN/TCP Seq per repair**. No second FEC logical source, parity, new AEAD PN, business/Health or delivery credit. Game/off v3 path remains unchanged. A native test gate now fails if Windows's real `copied_appearance` is zero, rather than passing on generic application success.

H814 [actual signed Windows NPF/Wintun ↔ WSL2 Linux Game2FEC6 1Mbps/25ms/10% loss/10s Action41338211724](https://github.com/lly8666/wbd-next/actions/runs/41338211724) **ALL SUCCESS** including Linux Rust, Windows Rust/Go and original native job124943594045. Actual downloaded/unzipped 43-file [artifact13096042611](https://github.com/lly8666/wbd-next/actions/runs/41338211724/artifacts/13096042611) (56652 bytes, `sha256:ddb60d61b7aa00373e9c62e345740761f6a306ada4801a9debd77ff4b1d52597`) has:
- `WBD_GAME_FEC_NORMAL_OUTER_STOP copied_appearance=310 sampled_original=[4265,4265]` **nonzero original Windows signed NPF driver copies**, versus prior 0.
- `WBD_GAME_NORMAL_SHARED_OUTER_STOP` lane1 and lane2 `repair_accepted=153/153`; `candidates=0` is the *gap-specific cosmetic* diagnostic, NOT the timer's actual first repair count. Linux same-run real outer78. Explicit positive test gate `windows_game_outer_copied_appearance=310` passed in report.
- True Windows↔Linux kernel UDP/TCP PASS, Windows/Linux first delivery fractions **1.0000 / 1.0000**; Rust native TX/RX join `0/0`, both owned Stop PASS, `wal_restored=1`, original product WAL/routes sidecar absent.
- No larger perf tier or Game4/abnormal exit five-stage WAL proof inferred. PTO appearance retransmission can select an actually received packet with unavailable ACK feedback, so do **not** claim its 310 packets repaired application delivery or FEC loss; the user requested cosmetic presentation and deferred optimization.

This is the first source-verified **functional PASS for Windows actual copied external GameFEC appearance retransmits** after prior zero. Stop here; no new optimization, rate sweep or auxiliary Actions in this task.

```feature-impact
{"kind":"updated","ids":["game-fixed-fec"],"reason":"H815 records source-bound true Windows NPF Game2FEC6 cosmetic outer 0→310 after H814 Normal receipt/PTO repair and owned Stop PASS in the existing feature card; no new product code."}
```
