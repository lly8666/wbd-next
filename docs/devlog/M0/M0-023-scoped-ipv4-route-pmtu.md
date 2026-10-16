# M0-023 protected scoped IPv4 route budget

CODE SOURCE: 2fd041352a0fd4fe63aba965b3ddff47d7ff8553. Formal M0-023 PARTIAL; one normal-build route budget atom complete.

M4 Linux reads real kernel IPv4 cached route PMTU using an interface-bound connected UDP socket with SO_BINDTODEVICE and getsockopt IP_MTU. It sends no traffic, validates interface index, name and destination, and compares the local interface MTU. This is not remote PMTUD success or raw packet I/O.

Normal-build Rust ProtectedScopedOwner binds that route to the original owner id, full epoch and generation, and original credential-checked Go V4 SYN peer MSS. ScopedLinuxBudget uses the existing M3 Normal/FEC-off budget and re-queries kernel route MTU before actual Rust AEAD/PN and M1 scoped FrozenRecord TX. Different index, MTU or stale generation fails closed before a new PN.

Exact SOURCE Actions native https://github.com/lly8666/wbd-next/actions/runs/38838714430: build job 116773573867, consume job 116773919359 both SUCCESS. Six Go top-level tests, all three cipher suites and Rust owner1/1 PASS. Build artifact 12020352082 SHA256 06a384b91bdd13812c86893025ea097ee41cd9fea9e13c3c1af331c6378fbc2b; result artifact 12020257335 SHA256 0d6f3ea15f9f74cbaf15fa14e2058c7962d6260f5c5dea8eec421a7f3bc8db21. Build-once/consume verified source/run/attempt and input and compiled binary hashes.

Native functional run 38838714332 platform 77/77 PASS including real kernel lo route lookup and bad-index/multicast-safe input negatives; ABI 38838714356, cross-build 38838714300, G2 38838714243, fake-platform 38838714157, Governance 38838714307 and R0 static audit 38838714234 all SUCCESS. Full maintenance 38838714447 169/169 PASS. Component-perf 38838714361 succeeded but DOES NOT qualify product performance.

Still NOT_RUN: production trusted Go-to-Rust V4 control or independent native provenance, real M4 raw/TUN driver I/O, kernel driver-held Stop B01-B04, physical remote PMTUD, end-to-end application delivery, fragmentation TX and 500Mbps. Production ABI features0. No untrusted self-consistent 248B cold is an authentication authority.

Next: secure versioned production control and actual driver lease joined to one owner; prove Linux first business both directions and Stop B01-B04 with exact-source Actions before enabling product capability.
