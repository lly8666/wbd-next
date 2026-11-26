# M0 dual Rust TCP — original Normal owner WIP

Previous exact SOURCE 3e709e0: 329 tests each native ISA and independently recorded endpoint receipt; current branch 7b15225 only evidence/docs. Main H2450 current; branch governance 45807286675 feature declaration and 121 tests passed, inherited H2416 cursor still fails structure check. No repetition of earlier component-only validation.

Implement paired Linux Normal/off (--dual-rust-tcp, existing shared auto-lease TUN, server lease-pool). Original post-AEAD/replay LINK admission keeps generation/lease check, diverts TCP only to same generation's original TX queue (not a TUN/app delivery counter), leaves UDP and other IP path untouched. The existing native TX worker alone owns client local/middle TCP and server origin TCP flows. Epoll origin readiness and indexed TCP deadlines with coalesced eventfd wake for original shared TUN/RX producers. No new worker, second TUN or Go packet FFI. Local replies use original TUN; middle segments enter existing M1/M3/M4; Rust derives inner MTU. Go cold flag makes both ends select same experiment without wire changes; original splice mutually exclusive and retained. Owned Stop drops flow table and sockets in original TX join. Original FEC/Game paths not yet connected; this is not a claim about them. Server-local TCP/source-policy semantics, early admission/reconnect, multi-lease, ACK/copy cost and performance still require targeted qualification before promotion.

Native functional fixture uses four existing-style actual kernel netns with original Go TLS + Rust RAW/TUN, client real OS TCP -> native endpoints -> origin real socket, exact 2MiB upload / 3MiB download, eight concurrent flows with one delayed reader, UDP echo, first response timing, actual client and server Stop. Both native ISAs use original glibc2.31 assembly and exact binary manifest. No perf comparison or physical claim. New SOURCE not yet tested at this commit.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Paired Normal native owner/CLI/real product fixture, not yet qualified."}
```
