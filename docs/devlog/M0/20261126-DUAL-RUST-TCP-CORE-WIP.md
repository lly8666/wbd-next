# M0-DUAL-RUST-TCP — first core WIP

Task baseline: 26b11e2da236e909b73f461964c52d5a86d42dca. Main registration at 849631e03ec0b9fd323d5a4384910c435219e5d7. Original splice remains available for same-job comparison. Its H2480 run 45791400655 had no valid offload intervention; job E failed in WSL preparation. Initial branch governance run 45801138238 failed before this increment. Neither is a new core qualification.

Port fixed pktkit TCP core with upstream MIT and source pin; retain existing toolchain and Cargo graph. Add capacity-limited transfer between two single-owned TCP connections with reusable caller scratch and both directions' ECN metadata. Use the existing upstream event deadlines, not a new polling controller. Add one transfer unit test; this is not a TUN/origin test. Branch-only native ISA unit build request is included. All results are NOT_RUN at this commit.

Remaining: Linux original TUN/client owner and server origin socket/flow ownership integration; wire real IPv4 inner segments and deadlines, checksum, MTU, generation, FIN/RST and Stop; genuine bidirectional application and UDP regression on x86_64/ARM64, then same-job A/B vs splice. No change to outer wire, authenticated handshake, FEC, old splice, GUI or default routing. No physical deployment.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Source-only experimental TCP core and bounded stream-transfer increment; no product entry enabled."}
```
