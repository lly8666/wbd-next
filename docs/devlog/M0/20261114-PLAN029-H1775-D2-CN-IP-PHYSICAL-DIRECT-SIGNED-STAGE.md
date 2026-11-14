# PLAN029 H1775 | nonCN DNS A→CN IP real Direct converse source stage

- Collected H1774 source \`034dbf3\`: Actions [43536191345](https://github.com/lly8666/wbd-next/actions/runs/43536191345) M0 cheap **SUCCESS**, [43536191265](https://github.com/lly8666/wbd-next/actions/runs/43536191265) original-Go Windows source build **SUCCESS**, [43536191271](https://github.com/lly8666/wbd-next/actions/runs/43536191271) governance **SUCCESS**. These do not prove a new physical network scenario.
- Added a new **NOT_RUN until H1775 Action** D2 scenario to the existing signed one-Wintun/one-Linux-TUN runner: original Tunnel DNS \`1.1.1.1\` answers nonCN \`cn-ip.globalx.example\` with \`198.19.254.2\`, an explicit test-only non-RFC1918 CN /32 in the cold geodata file. Real Windows Wintun-bound app sends UDP to that A, requiring Rust physical Direct source seen by independent Linux eth0 socket and exact echo. Existing \`203.0.113.77\` nonCN A→Tunnel comparator runs earlier unchanged.
- One test-only Windows physical /32 route and one Linux eth0 /32 alias are journaled before Apply and owned-cleaned by exact SOURCE, peer, ifindex and address even on failure. Application uses explicit Winsock Wintun ifindex because on-link physical /32 would otherwise bypass capture. This **does not** prove ordinary on-link/physical-bound apps are intercepted; no bulk routes, WFP guard or test ACK.
- New Linux/Windows socket fixtures, strict PowerShell outer oracle, log names and syntax/source shape checks. Record first FAIL and true Stop; no invented PASS. D1 TCP53, full CDN/TCP cases, D3–D5 and P1/P2 still OPEN.

\`\`\`feature-impact
{"kind":"none","ids":[],"reason":"This batch changes owned signed D2 test fixtures/oracle and audit only; product feature card is unchanged until real network result."}
\`\`\`
