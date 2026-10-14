# R1-M3-LINK-REASSEMBLY-004

Old Go oracle: pinned wobuzhidao@a7a82db3 internal/linkdata/datagram_fragment.go and _test.go, plus r0/fixtures/legacy-link-fec-wire-v1.txt. This Rust M3-only task implements bounded authenticated-LINK-input reassembly (not AEAD itself) with zero-copy ordinary hot bypass, 20B frozen Go LINK header only on fragments, out-of-order complete, packet_id extended with tunnel epoch/direction, 16 outstanding assemblies, <=1MiB buffered business, <=1MiB conservative metadata accounting, max64 compact retire, absolute mono 5s assembly TTL and 10s compact TTL, deterministic oldest eviction, no missing-packet HOL.

Deliberate divergence: original Go conflicting duplicate returned conflict but *retained first arrival*; current docs/architecture/modules/06-LINK-MTU.md requires entire conflicted assembly retired. Our conflict policy is stronger, not a false claim of byte-identical conflict behavior. The old Go count==65535 sparse-metadata acceptance is also narrowed by an explicit minimum frame budget and layout check; no unbounded parts[count] preallocation. Inputs must already be authenticated record bytes, with scope/monotonic time from owner; no link-level fake authentication. M0 owns integration and shared ABI/root Cargo.

S native Actions NOT_RUN until new source/workflows finish; preserve source and failed attempts in evidence.
