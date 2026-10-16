# M0-023: credential-checked Go FakeTCP flow capture

**Subatom result: PARTIAL_GO_PROTECTED_TUPLE_CAPTURE_PASS. Formal 023 remains partial.** Exact CODE SOURCE `a9b9dd5d523e56145404e675adf43ba9066a4e39`; detailed run/artifact receipts in [evidence](../evidence/M0/M0-023-Go-protected-flow-capture.json).

Why now: previous true Linux raw/TUN first-packet probe still used a fixture TCP tuple; production Go private V4 owner handoff saw real SYN MSS but not the original FakeTCP four-tuple. This is the smallest actual Go control-path change toward binding real native owner identity and transport sequence domain.

Code S changes the existing private `v4PeerTransport` to copy `assoc.Flow()` (client/server IPv4/ports) alongside SYN MSS, reject invalid observed tuple, and reject a tuple change between protected Prepare and post-reply Detach/Commit. It adds `TestR0V4AssociationFlowScopeComesFromOriginalFakeTCP` and tightens the existing real protected V4 recording-owner assertion. No extra round trip; Prepare → protected reply → Detach → Commit remains unique.

Exact-SOURCE GitHub Actions all concluded success: 13/13 real Go TLS/admission (including new test), 6/6 Go control groups, 1 Go+4 Rust cold grammar, private Go/Rust native + 3-suite true kernel raw/TUN smoke, governance identity/structure. Build/consume job identities and GitHub artifact digests are exclusively in evidence. No local tests. Governance drills/model NOT_RUN; cross-platform/product claims are not inferred.

Still open: Native production Rust authority/versioned command and bound genuine flow/seq, B01–B04 held M4 driver stop/reconnect, veth netem RTT/loss/reorder, product normal performance, physical/500Mbps; ordinary features=0. Previous true loopback fixture [evidence](../evidence/M0/M0-023-true-raw-bidirectional-tun.json) retained. **One next action:** connect this protected Go association/credential source and precise RX/TX seq to a reviewed ordinary Rust scoped-owner admission path without accepting arbitrary cold248 as authentication.
