# M0-023: actual kernel M4 scoped UDP V4 TX first packet

Exact CODE SOURCE: `128bc6603c54272b0a60b0029465ed6da6e855d4`. **Bounded Linux-kernel-IO subatom PASS**, not production product qualification.

User rightly identified excessive repeated MSS/MTU/route probes. This atom instead joins the same normal-build Rust V4 `ProtectedScopedOwner` with the EXISTING normal-build M4 `ScopedUdpOwner::submit` → Linux `sendmmsg`: owner verifies Active + correct M4 generation + nonstopping; takes M1 scoped TX LoanBatch, clones only immutable Arc-backed FrozenRecord handle(s), keeps loan alive across actual send syscall, returns full `BatchResult` including accepted/uncertain without retry. No alternate record crypto, no standalone queue, no fabricated byte delivery.

The private Go real protected TLS server (3 cipher suites) creates the Rust owner after genuine protected reply, Go Detach and exact SenderNext. A test-only glue function creates real kernel loopback UDP sockets and directs the actual M4 driver send to Go's independent `net.ListenUDP` receiver. Go's TLS-derived client `Opener` authenticates the two ciphertext packets received through kernel socket, PN0/1, exact TCP seq and plaintext. Negative: precommit, wrong ifindex, missing destination and after-Stop fail. **UDP sendmmsg copy-complete is not a remote peer receipt.** This is a concrete kernel hop, but not TUN/raw or production user application I/O.

Exact [native Go→Rust run 38840290787](https://github.com/lly8666/wbd-next/actions/runs/38840290787) attempt1 build116778580666 and consume116778946302 SUCCESS; seven Go top-level tests (new kernel first-packet with all 3 ciphers), Rust owner1/1 PASS. Build-once/consume SOURCE/run/attempt/input/binary SHA256 checked. GitHub API artifact build12021415619 digest `sha256:d929c7f6f82d52c40a5d45d692501f10e82d6f887c8150af4b47efc11d55d4e7`; result12020489447 digest `sha256:cd36811060031f99e48b3f560b362e3dd190c86fe9472b0c9f04d5b62140bbb9`. Artifact ZIP not independently downloaded and rehashed.

Same CODE SOURCE native-functional38840290701, native ABI38840290697, cross-ABI38840290705, G2 38840290736, Governance38840290717, R0 static38840290739, and maintenance38840290712 all SUCCESS. Windows/ARM cross builds are not native runtime tests.

Remaining: genuine kernel C2S→M4 RX→M1 borrowed owner→AEAD/M3 completion; production Go authenticated native control command (plain self-consistent 248B cold cannot authorize owner), real TUN/raw application endpoint, M4 held driver loan Stop B01–B04, loss/partial send policy, physical E2E, 500Mbps/CPU/p99. Product capabilities/features remain `0`; qualification still NOT_RUN.

Next shortest vertical slice: real Go kernel UDP C2S transmission to M4 scoped recvmmsg directly into an M1 UniqueBuffer and the SAME scoped normal Rust AEAD/PN and LINK receive callback; then true kernel driver-held Stop; separately complete secure production control and final TUN/raw. No further standalone MTU probes.
