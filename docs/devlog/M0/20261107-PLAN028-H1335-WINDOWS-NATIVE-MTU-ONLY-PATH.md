# PLAN028 H1335 — native Windows selected physical MTU-only reauthentication

Restored main 5bb60800901fcd1c828db7074a8434a05292a0a2 cursor H1334; no in-flight Actions. Windows cold OS product previously compared only physical ifindex and source IPv4, ignoring same NIC/IP MTU-only changes, violating PLAN028 L0/L1 hard path gate. Changed only existing Go cold native watcher: NotifyIpInterfaceChange subscription, selected physical IPv4 MTU fingerprint, same 200ms/500ms coalescing, original Go TLS after exact previous Rust/WAL Stop, Rust cold budget and actual new Wintun MTU readback. No new TLS prelude, data-plane loop, FEC/record format, Go hot packet transfer, or user outer default change.

One targeted original signed Npcap/Wintun Windows2025↔genuine Ubuntu WSL2 Linux Normal Off mode. On test-owned WSL vEthernet only, same ifindex/source IPv4 198.19.254.1, real OS NlMtuBytes 1500→1280, verify original SYN MSS1420→1240, Windows Wintun inner OS1389→1209, original TLS/M4 cohort B, true post-B kernel UDP/TCP, owned Stop and full restore before exit. Runner default route unchanged. The WSL CI-owned MAC override exception requires exact guest, OS-selected source/ifindex, second generation, 1280 physical readback; negatives included. Original H1135 different OS source .1→.9 2 generations PASS is separate; H998 original same-socket MTU shrink FAIL retained.

VM comparison is not a universal multiplier: H1332 x86 four-vCPU 50Mbps/dir 59.63% busy is valid only for that guest/traffic; record Windows VM actual cores/logical vCPU, RAM, real sender PPS, CPU and OS paths before any performance comparison. No source-locked Windows network result exists for this new code yet: `NOT_RUN`, not PASS. Other six-mode lifecycle, WAN/physical NIC, Android and L3 remain OPEN.

```feature-impact
{"kind":"updated","ids":["path-mtu-budget","windows-native-transport"],"reason":"Windows native selected physical NIC IPv4 MTU-only event now enters existing cold original TLS/Rust reauthentication and verified Wintun OS path; scoped real Windows test and VM capacity receipt added, outer MTU default1460 unchanged."}
```
