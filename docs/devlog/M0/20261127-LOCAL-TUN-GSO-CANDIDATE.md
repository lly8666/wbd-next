# Local TUN ready GSO candidate — unverified

05bb056 native45932877384 both ISAs functional PASS after TIME_WAIT repair. ARM45932877398 completed BBR0 4/4 with direct endpoint snapshots, bare564.3657 Mbps, splice291.4751 vs Rust151.1196 Mbps, CPU/GiB 26.7722 vs40.4250. Client ZIP15169921138, server15170041643, relay15169796355 inspected; B1/B2 client local DATA869052/801877, ingress full18697/18781, shared TUN full56617/68804, local write failures0. Server M4 copied1158231/1052684, no unmatched/uncertain. No performance promotion.

Candidate: client-only opt-in VNET_HDR at original Go TUN creation, explicit offloads disabled for OS-to-Rust reads. Rust detects 10-byte ABI from exact FD, strips local metadata on reads and prefixes ordinary writes. Only compatible contiguous equal-size ready TCP DATA from the existing local output turn may use one GSO skb: same tuple, header/options/ACK/window/flags/ECN, no gaps or short tails, max32; scatter writev references existing payload slices, no payload aggregate copy or wait. Timestamp all component attempt receipts, never retry failed aggregate. UDP and singleton datagrams unchanged except local device prefix. No outer format, encryption, MTU, FEC or repair change. No Windows implementation or claim, no bidirectional kernel offload, no extra queues/threads.

Native exact product tests original/parity plus GSO profile on both ISAs, positive actual local GSO copied receipt required; one BBR0 narrow ABBA compares against old splice, not isolated GSO causality. GSO implementation and native kernel compatibility unverified until Actions. Main old splice retained.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Client-only local TUN writev GSO candidate, actual native receipt qualification and prior BBR result; no outer change or promotion."}
```
