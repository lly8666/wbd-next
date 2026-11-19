# H2216 Actions root-cause triage — 2026-11-19

## What was failing, and why

| Evidence | Root cause | Status after this change |
| --- | --- | --- |
| H2216 44489846700 Linux | New Go realityfront test enables `wbd_v4_native_probe`, which includes legacy probe test still using removed `faketcp.DefaultMSS`; the current FakeTCP public API is `PublicV4AdvertisedMSS()` | Fix 7 probe uses; actual Linux V4 test remains mandatory |
| H2216 44488389171 Linux | Excluding probe tag removed test helpers `v4RawCheckSum`, `v4RawC2STestPacket` | Retain probe build tag and repair its dependency, do not skip testing |
| H2216 444895* and 444891* | Workflow YAML / shell / PowerShell quoting mistakes prevented jobs from starting | Previously repaired; keep native workflow syntax and run once per consolidated source change |
| H2216 44485809254/44486850281 | Game4 certificate verification failed; old EstablishClientV4 unconditionally forced `VerifyServer=true` despite the CLI `--tls-verify-server=false` default, and Game2/Game4 Linux also forced true | Fixed in earlier main commits; real V4 test now exercises Normal+Game |
| H2216 44484179359 Windows | Old Game test incorrectly treated TTL=128 as proof against Legacy TTL=64 | Update expectation: TTL is never authentication |
| Earlier governance | Feature card exceeded 16 KiB after verification additions | Historical evidence archived; latest governance at 71c4fd3 PASS |
| Repeated full runs from tiny changes | Workflow itself was in push paths, no same-branch cancellation | Add concurrency cancellation and remove purely documentary feature-card trigger |

## TTL inbound policy

The original Go packet parser does not use TTL as peer identity. The Rust
native DATA and ACK parsers should likewise ignore the sender's persona TTL:
every received nonzero TTL is acceptable. The IP header checksum remains
mandatory (router updates it), as do TCP pseudoheader checksum, full trusted
tuple, bounded lengths/options, authenticated M3 AEAD, PN replay, generation
and owner. TTL=0 is an invalid IPv4 header. The parser returns only untrusted
ciphertext/ACK metadata, never an authenticated payload.

## Qualification and gates

1. Actual six V4 self-signed verification switch cases compile and execute,
   with Go's pinned FakeTCP sources and probe test helper wired correctly.
2. Windows Rust native owner and 419 GUI smoke/self tests must pass.
3. Native Linux ARM64 compiler and parser test must pass.
4. Three independent client-SNAT LANs, server DNAT on TCP443, genuine
   original Go TLS + Rust TUN/UDP echo/Stop; separate Game4 stress remains
   visible when it fails.
5. Same-source Windows + ARM64 package is field-trial until actual
   Windows↔ARM64 ISP/public Internet passes on physical hardware.

No success is claimed from this documentation or a pending Action.
