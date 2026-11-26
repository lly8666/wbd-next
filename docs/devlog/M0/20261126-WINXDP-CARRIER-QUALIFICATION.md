# M0 WinXDP carrier experiment — qualification, not product PASS

Base: 26b11e2da236e909b73f461964c52d5a86d42dca (H2480).
Branch experiment/m0-winxdp. No protocol, appearance, Wintun, or Linux product changes.

Sources: Microsoft XDP for Windows v1.3 production SDK/runtime, AF_XDP shared SPSC rings, XskBind per queue, XskNotifyAsync, upstream usage documentation. Generic NDIS mode does not imply NIC zero-copy; RX redirects instead of Npcap's passive copy. Built-in rules are deprecated, and TCP destination-only rules cannot substitute for the existing exact-flow BPF. Product RX needs equivalent flow steering (evaluate eBPF exact tuple and queue coverage) plus atomic cold reader handoff. Physical Native mode separately unqualified.

First action verifies actual signed runtime, SDK header-only API, WSL vEthernet generic bind, real guest RX->TX via a dedicated UDP fixture port, 64 returned packets, TX completions and ring statistics. RX and TX share the same registered chunk in this echo fixture; WBD encryption/decryption has different ownership and cannot automatically reuse it. The fixture is NOT WBD traffic or ABBA. No new product worker, no product defensive framework. No test-signing changes.

Product plan: reuse two Rust workers and original Wintun lease, separate RX and TX UMEM ownership; borrow RX descriptors until existing M3 processing finishes, then batch recycle; stage existing Ethernet bytes directly into TX chunks where lifetime permits; retain immutable repair ciphertext separate from reusable TX chunks unless ownership proves reuse; TX acceptance maps to descriptor submission, completion to reclamation (not remote delivery). Use XskNotifyAsync with existing stop/direct/wake events, no busy polling or waiting to fill batches. Cold TLS path must also migrate for full Npcap removal. Retain actual lane-generation and Stop semantics, do not change wire. Investigate queue/RSS count and flow handoff before selecting implementation.

Follow-up performance: reuse H2480 9V45 gate + WSL topology, build source-locked A/B, run same-host ABBA/BAAB 250/650Mbps at 400ms; compare remote real goodput, CPU/GiB, kernel CPU, small flow latency and drops. This action only qualifies carrier; no performance claims before actual results.

## Evidence
- Run 45802274940: NuGet SDK/runtime 1.3.0 installed; SDK compile failed due missing XDP_INCLUDE_WINCOMMON. Fixed 79d9e6d.
- Run 45806115287: compile/install + WSL success, XDP Generic socket/redirect READY ifindex25 queue0. Guest UDP timeout; fixture killed probe before statistics, no RX/TX attribution. Next probe preserves joined statistics and compares OS UDP echo before XDP, logs batch RX and completion and actual RSS/bindings. Unconditional batch TX poke isolates wake handling; not product pacing policy.
