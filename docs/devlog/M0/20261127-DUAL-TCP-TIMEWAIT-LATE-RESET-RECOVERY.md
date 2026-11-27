# Dual TCP orderly close recovery — unverified

495586c769d485b9916a80cd5b9f239fb1f98fb0 native45931633269: ARM PASS, x86 core344 and exact M4 unit PASS, ordinary Normal PASS, parity concurrent application reset FAIL. ARM45931633292 prepare blocked; no measurement. This product source is identical to prior 392ee06 functional PASS. x86 job140285357638 and original ZIP15167969292 reviewed. Server middle RESET_NO_FLOW ACK for tuple source port52200 seq1036114742 ack3113320624; client RESET_ACCEPT TimeWait seq3113320624, then local RESET_NO_FLOW same flow; app reset. Client ingress full0, server full77, client/server M4 copied3193/9803, no not-proven/no-PN. No causal claim M4 clock itself caused it.

In current Conn synchronized RST path, accepted reset in TIME_WAIT tears down as abnormal. ClientFlow drive aborts the other leg on abnormal_end, even though middle FIN exchange already completed and local delivery may be draining. Keep existing TIME_WAIT lifecycle on late RST instead of propagating a false business abort. No extra state, timer, queue, network packet or outer change. Add regression of real core close sequence, late final ACK to closed peer, resulting RST, retained unread bytes and unchanged deadline. True established-state resets unchanged. This directly addresses observed trace; exact complete causal chain and ingress loss remain subject to native requalification.

Existing narrow BBR0 ARM parity intent retained, new exact-source native qualification then same ABBA. No bypass of failed x86 gate, no repeat old source. Main H2478 governance45931683700 PASS; preserve historical FAIL. No product promotion.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Fix observed inner TCP TIME_WAIT late reset causing cross-leg abnormal close; add regression and native requalification."}
```
