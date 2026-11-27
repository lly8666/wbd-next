# Consolidated Linux TCP behavioral alignment — unverified

Prior SOURCE 935a6317969486846fec60fe98f35d2429dfedcb: native 45914393727 dual ISA 339/339, original/parity scoped product PASS. ARM hotpath 45914393841 8/8 measured: BBR0 A=286.301/201.627 B=237.533/193.610 Mbps, endpoint CPU-s/GiB A=30.562/38.039 B=35.704/37.228; CUBIC0 A=202.347/275.210 B=270.136/325.241 Mbps CPU A=50.526/43.044 B=42.327/37.491. Mixed grouped results, not causal individual attribution or promotion.

| Linux function | Current parity candidate |
|---|---|
| tcp_sacktag_write_queue / tcp_clean_rtx_queue | Delivery.packets; count completed records, not bytes or ACK messages; split records not identical to skb pcount |
| cubictcp_cong_avoid / bictcp_update / tcp_cong_avoid_ai | packet growth, 5% initial floor, integer friendliness, 717/1024 reduction; float target and time quantization still partial |
| hystart_update | threshold/sample count refinement; actual GSO/ACK train timing different |
| tcp_rtt_estimator | scaled SRTT, asymmetric mdev, per-send-round max/decay, 200ms floor; sample selection and timer resolution remain partial |
| tcp_minshall_check / tcp_nagle_check | track outstanding short-tail end; SWS/FIN preserved |
| tcp_retransmit_timer | SYN6/SYNACK5/data15 retry counts; Linux elapsed-time and orphan policy not identical; owned Stop unchanged |
| tcp_update_pacing_rate | parity SRTT; bounded owner pacing differs from skb EDT |
| bbr_lt_bw_sampling | two stable loss intervals, 4–16 rounds, loss/delivery 50/256, rate proximity 1/8 or 500B/s, 48-round expiry; byte-based |
| bbr_quantization_budget / bbr_tso_segs_goal | model allowance, even packet rounding, probing margin; no actual TSO/GSO/EDT |
| bbr_is_next_cycle_phase | prior flight, not historical sampled packet flight; EDT projection missing |
| tcp_rcv_space_adjust / sndbuf_expand | prior payload growth, not skb truesize |
| tcp_rcv_established | header prediction / allocation-free receive parser NOT implemented |
| tcp_small_queue_check / tcp_write_xmit | owner pending/admission/sent-time still NOT aligned |
| AccECN extensions / PLPMTUD | missing or disabled; preserve product MTU |
| splice skb page ownership | intentional architecture difference |

Upstream v7.0 reviewed; exact Ubuntu patched trees 1020.21 /1017.17 not independently compared. Independent behavior implementation, no verbatim GPL code. No new queue, worker or outer protocol change. Native dual ISA then one grouped Linux splice vs Rust CUBIC/BBR 0/1/5 ABBA (24 legs). Candidate unverified.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Consolidate Linux TCP congestion control, RTT and Minshall mechanisms in experimental profile; actual offload and owner differences remain; no default promotion."}
```
