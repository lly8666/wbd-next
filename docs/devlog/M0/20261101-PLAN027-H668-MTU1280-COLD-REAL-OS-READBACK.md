# H668 — actual Windows/Linux native MTU1280 original TLS configuration, not a JSON-only intent

PLAN027 B requires path/native MTU readback and genuine app/Stop, while current `tools/m0_wl_perf_v2_config.py` parsed `tun_mtu=1280/1400/1500` but `tools/m0_wl_public_normal_e2e.py` always took `WBD_WL_TUN_MTU` default1400. Reusing a 1280-labeled V2 scenario without setting that environment silently tests 1400—not acceptable.

H668 minimal source-scoped fixture change: `m0_wl_public_modes_e2e.py` passes immutable parsed `tun_mtu` into **the actual original Windows native Go --mtu CLI before TLS**, and `m0_wl_public_normal_e2e.py` compares that runtime configured value to scenario. Only for the new 1280 B scenario, it then reads the **actual Linux kernel `ip -j link show dev wbdwl4`** after both original credentialed TLS products are Ready, requiring an unambiguous TUN device and MTU <=1280; must still pass real original dual kernel UDP/TCP and owned Stop. This does not fake a new network acceptance handshake, change Go/Rust product, report packet-level 1280+1 reject or claim dynamic in-place PMTU/physical PASS. Other registered 1400 scenarios keep exact behavior.

One SOURCE5fb4 artifact-reused original Normal 10Mbps/25ms/0/60s independent Action, Windows manifest13052066362 and Linux13051752044 from build run41224887969. Same VM single scene, no duplicate compile. A failure from actual OS MTU mismatch is genuine B wiring defect, distinct from host capacity or a source guard failure. H664 B106 and H667 GameFEC min stay independently IN_FLIGHT.

```feature-impact
{"kind":"none","ids":[],"reason":"Test-only original Windows native scenario-MTU setting and actual Linux kernel post-TLS readback, one original scoped 1280B scene; no runtime or product feature changed until verified."}
```
