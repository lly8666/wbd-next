# M0 Linux TCP behavior parity — first consolidated candidate (NOT qualified)
Audit baseline: old splice 26b11e2da236e909b73f461964c52d5a86d42dca; Rust 182bd73efbd159a52dba6f827be0bdd53ad0c874; experiment parent 40bfca1a8d327f155f20511f86b3ffa20ae8c83a. Prior matched ABBA 45845854268: kernel ABI 7.0.0-1020-azure, tcp_bbr srcversion 5B6C12777290291DF28F230; exact Ubuntu binary/source revision remains unverified. Upstream reference v7.0, not assumed identical. Linux rcv_rtt_est.rtt_us is scaled by eight: >>3 restores RTT, NOT RTT/8.
 
| Linux function | Rust function | Classification / candidate scope |
|---|---|---|
| tcp_sendmsg_locked / tcp_write_xmit | write / flush_send_queue | partial; Nagle on in parity; packet vs byte quotas still differ |
| tcp_sndbuf_expand / bbr_sndbuf_expand | sndbuf_expand / sndbuf_target_with_factor | partial; BBR1 factor 3, both endpoint caps 64 MiB; actual skb truesize and backpressure not equal |
| tcp_rcv_space_adjust / tcp_rcvbuf_grow | RcvSpace.adjust | partial; RTT period retained, unread and low RTT growth/OOO cost remain to audit |
| tcp_event_data_recv / tcp_send_delayed_ack | note_data / ack_data / tick | partial; ACK2 and adaptive ATO first approximation |
| tcp_sack_compress_send_ack | defer_sack_ack | partial; RTT33% 1ms ceiling, no exact separate hrtimer or block rotation |
| cubictcp_cong_avoid / hystart_update / cubictcp_recalc_ssthresh | Cubic | partial; legacy HyStart-style experimental path, cwnd-based loss and ECN beta; fixed point/ACK train edge cases not identical |
| bbr_main / bbr_lt_bw_sampling | Bbr1 | partial / missing policer model and TSO compensation; no BBRv1 equivalence claim |
| tcp_rtt_estimator / tcp_retransmit_timer | RtoState / sample_rtt | partial; per-sample gains and 120s cap, retry policy/variance filters remain |
| tcp_ack / tcp_sacktag_write_queue / tcp_rack_mark_lost | process_ack / Scoreboard | partial; old ACK and DSACK/recovery ordering require trace audit |
| tcp_data_queue_ofo | RecvBuf.insert_ooo | partial; adjacent range fast paths, unchanged 500k-segment test budget and added bridge/duplicate regression |
| tcp_rcv_established / tcp_tso_autosize | generic packet parser / send_new | missing dedicated fast path and aggregate offload; not faked |
| tcp_splice_read / skb page ownership | read_to / transfer | deliberate different userspace ownership, copy/alloc cost not yet addressed |
| tcp_small_queue_check / pacing / socket timers | native owner, pacer, shared budget | architecture difference, previous ingress-first negative; bounded pacing, no queue enlargement |
| tcp_accecn_process / tcp_mtu_probe / tcp_fin | Ecn / plpmtud / FIN state | partial; AccECN option absent, fixed product MTU; full lifetime behavior not proven |

Profile WBD_M0_LINUX_PARITY=1 only, previous production path retained. Native functional and full core on both ISAs precede real ARM three-VM matched Linux splice A / Rust B ABBA for CUBIC and BBR1-style, each 0/1/5% loss, 400ms added RTT. Kernel package/config/sysctl receipt added to snapshots; missing receipts or divergent actual versions preclude exact parity. Existing old binary SHA and exact same-commit candidate bundle required. Test results pending; no main merge, old splice retirement or performance claim. Combined candidate is not individual causal attribution; follow-up single-factor ABBA needed. Linux kernel TCP and Rust code should retain license separation; implementation independently derived from observed behavior. No TLS, carrier, FEC or global queue capacity changes.
