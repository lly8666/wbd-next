# H2219 — paired physical capture: the third cold control/Health segment disappears

2026-11-19, M0. User interrupted the previous cross-runner effort and supplied two paired physical Linux/Windows H2216v2 captures. Original uploaded packet ZIP SHA256: `39d9f3e62d739247713df03204f67dfd838530edc09097c5ff681ca09a3719a8`. Underlying binary hash not provided; user reports SOURCE prefix `91b9d52`. No raw pcap, private/public IP, credentials, or full packet data committed.

**Round 40015:** Linux `enp0s3` native server post-M4 sends seq `4016913351:4016913447` 96B (18:46:20.264), `4016913447:4016913564` 117B (20.664), `4016913564:4016913629` 65B (21.064) in **exact 400ms increments**. Windows acknowledges first two through `4016913564` but NIC/Npcap components have no third 65B. Next server 74B from seq `4016913629` appears 14.31s later, with no replay of missing 65B. Original ACK `4016913564` appears **39 times** in Linux pcap; Windows `RXDelivered=0`.

**Round 40016:** Linux native server emits `1909226370:1909226472` 102B (18:50:01.400), `1909226472:1909226536` 64B (01.800), `1909226536:1909226602` 66B (02.200). First two client ACKs advance; third 66B is absent from Windows NIC and independent Npcap even though the Linux egress capture saw it. Next 89B starting `1909226602` appears 16.47s later and does not fill the gap. ACK `1909226536` repeats **40 times**; Windows `RXDelivered=0`.

This 3×400ms timing precisely matches `crates/wbd-engine/src/v4_native_health.rs::arm_server_cold_commit` / `HealthClock::on_health_send_result`: 3 signed control-family cold receipts, then jittered nominal 15s regular Health. Source does NOT register the last `feedback_last` authenticated control in the Linux Normal `OriginalOuterRepair` DATA-only frozen shadow under `crates/wbd-engine/src/v4_embedded_go.rs`; the out-of-order later Health has a new TCP sequence and cannot close the prior cumulative ACK hole. This is a **clear reliability coverage gap**, but the exact AEAD record kind cannot be independently decoded from the **54-byte snapped** TCP captures. Do not infer the initial missing TCP segment was invalid/valid checksum: full TCP payload absent; Linux egress IP checksum and L2 next hop matched subsequent delivered segments.

**Causality boundary:** after Linux physical NIC egress capture and before Windows inbound packet observation, with possible hypervisor/cloud NAT/physical routing. Two independent captures support absent packet at Windows, but no intermediate hop and no full TCP checksum. Server TCP-like raw send syscall success is NOT proof of WAN delivery. No original-sequence retransmit was observed in either Linux capture. Windows 0 business RX may also need a separate server TUN reverse/outer AEAD gate check; successfully repairing cosmetic presentation ACK alone is **not** authenticated business success.

**First focused regression**: in original source native Normal (both endpoints behind independent NAT netns), inject exact loss of third 400ms cold Health, record true TX/ACK/RX/AEAD counters, implement only a bounded same-sequence frozen replay of genuine original control *if* necessary, prohibit extra PN, and prove actual TUN reverse packet and owned Stop. No unsolicited change to TTL, checksum enforcement, Go TLS or security model. Do not repeat unavailable cross-Azure GitHub hosted ingress as evidence for the user physical situation.

Structured: [H2219 evidence](../evidence/M0/PLAN029-H2219-H2216V2-PAIRED-PHYSICAL-THIRD-COLD-HEALTH-LOSS-20261119.json).

```feature-impact
{"kind":"none","ids":[],"reason":"User-supplied cross-host physical capture diagnosis recorded; no product code or feature-card change. Physical FAIL remains and existing NAT CI PASS_SCOPED is not promoted."}
```
