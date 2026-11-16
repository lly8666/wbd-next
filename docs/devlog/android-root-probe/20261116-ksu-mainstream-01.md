# Real Android KSU mainstream traffic single-AVD canary (2026-11-16)

User requests major mainstream use cases instead of recurring synthetic UDP-only tests. This new source extends proven Android16/API36 x86_64 real KernelSU Manager approved ordinary App UID10218→Root TUN, plus independent SIGKILL cleanup, in ONE emulator run/source/native binary.

In the same temporary AVD with SELinux Enforcing and only an app UID + synthetic /32 policy rule, ordinary App must:
1. Send real UDP DatagramSocket nonce, receive matching TUN-injected response;
2. Send a standards-shaped DNS A query directly over UDP/53 to synthetic peer and receive a verifiable IPv4 A answer (NOT Android's global/netd system resolver);
3. Complete a real kernel TCP SYN/SYN-ACK/ACK handshake, send HTTP/1.0 GET over Java Socket to synthetic peer; Root TUN must read actual SYN and HTTP request and return checksummed TCP HTTP200 segment; normal App must read nonce body, kernel must ACK native response;
4. Query Android ConnectivityManager.getActiveNetwork/LinkProperties, invoke Network.bindSocket on an independent App Socket, and prove real network-routed TCP to emulator host 10.0.2.2:18317 via host-owned TCP echo fixture. This is a genuine Android netd-selected default network, NOT actual Wi-Fi/cellular/routing service modification. It additionally proves synthetic UID route does not steal independent underlay traffic.

Same KSU CI checks source-locked native/targetSdk37, default network interface/route, route/rule before-after byte equality, TUN cleanup, and existing exact SIGKILL watchdog canary. No API matrix, no real device, no global netd route writes or NAT. Actual TCP/DNS/netd statuses MUST be proven by installed ordinary App and live host; no positive promotion until CI SUCCESS.

```feature-impact
{"kind":"none","ids":[],"reason":"Add one actual Android16 KSU App traffic canary for UDP53 DNS, raw TUN TCP HTTP and netd active-Network host underlay, while preserving /32 UID-only scope and SIGKILL cleanup. Not yet qualified."}
```
