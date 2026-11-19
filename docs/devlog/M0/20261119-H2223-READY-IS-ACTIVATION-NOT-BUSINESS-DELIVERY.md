# PLAN029 / H2223 — READY means authenticated tunnel activation, not receipt of arbitrary business

**Status:** source branch candidate only. Physical Windows ↔ Linux real NAT trial **NOT_RUN**. H2221 real physical Linux uplink M4/TUN fixed, but downstream business/Internet exit still **OPEN**.

## Root cause of false cold failure

H2216v2 physical Windows Original-Go TLS authentication succeeded while Windows Rust workers copied 27 outbound packets and delivered 0 application packets from Wintun; client aborted at the fixed 20-second `TXCopied >= 2 && RXDelivered >= 1 && TXAfterRX >= 1` readiness barrier. Physical R3 even had all four S2C post-auth records reach the NIC without application delivery. In an independent physical experiment, eight Linux-generated IPv4 tunnel probes led to `RXDelivered=8` and `WBD_WINDOWS_CLIENT_READY` for the same client/server versions. The old readiness predicate was an **application traffic generator requirement**, not TLS authentication or a locally usable tunnel requirement.

## H2223 minimal cold readiness

1. Original Go credential-verified TLS 1.3 and M3 session keys; no change to the handshake shape, certificate/account policy, or crypto.
2. The exact Rust M4 owner has started two native Wintun/NPF worker threads against the original session's bounded identity and device loans. One readback ensures no known native worker error. No new native C ABI.
3. The **existing** four-stage Win32 OS/WAL transaction fully Applies, validates its actual OS readback and current Wintun inner MTU, and retains the original resource lifetime/Stop discipline.
4. Emit `WBD_WINDOWS_CLIENT_READY` immediately. Application counters `TXCopied`, `RXDelivered`, `TXAfterRX` keep their original numerical meaning but do **not** gate cold readiness.

We intentionally do **not** add H2222 `READY_PROBE/READY_ACK`, Health timeouts, an extra TLS-like control layer or synthetic reverse traffic. An authenticated TLS tunnel with no user application traffic is a legitimate idle connection. `READY` therefore means *client activation*, not a statement that Ping, public exit, or future packet loss have passed an E2E test. Separate data-plane probes and Health90 remain diagnostic/steady-state monitoring; they are never retroactive conditions on local activation.

## Genuine cold network resilience, without a second protocol

The existing original Go FakeTCP SYN and TLS sender RTO continues to operate inside each real TLS attempt and is fully joined before Rust Detach. Only **explicit transport-phase timeout errors** can trigger at most two initial reattempts, spaced 1 and 2 seconds, each using the already source-locked fresh TCP source-port ordinal. Missing application replies, rejected credentials/certificates, user Stop, OS readback or driver errors do not trigger TLS reconnect loops. Existing authenticated-dead90 and physical IPv4 path recovery logic remains unchanged.

## Scope/compatibility

- Linux server code is the H2221 AF_PACKET M4 ingress candidate from exact source `c4e02b8512d802571e56794c554277653f6465c7` (no H2222 nonce extension).
- Windows original Go+Rust DLL is built from the identical H2223 source and the signed assembly manifest blobs. H2216v2 Windows with H2221 Linux still retains old 20-second failure gate; a **new Windows client** must be deployed to test H2223.
- The legacy explicit Go-steady A/B traffic verifier is unchanged. No network protocol downgrade or unauthenticated acceptance.

## Gates

- Unit tests: idle 0/0/0 and physical-like 27/0/0 both satisfy the native worker activation verdict; fatal worker rc rejects. Three-attempt first-TLS retry bounded by source and failure category.
- Build tests: actual original Go Windows executable + original Rust M3 DLL, real Go TLS 3-cipher integration, Linux ARM64 server original Go TLS/Rust M4 double NAT and Stop.
- Pending: authentic **physical** Windows ↔ Linux two-NAT smoke after the same-source paired binaries. `WBD_WINDOWS_CLIENT_READY` should occur without any traffic generator; run Ping/TUN business/public egress **afterwards** as an independent data-plane evaluation. If business still fails, do not recategorize as a startup failure.

**Conclusion:** remove a product false-negative readiness requirement; do not confuse this with curing intermittent underlay S2C loss.
