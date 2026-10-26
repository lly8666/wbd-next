# 2026-10-23 Normal P0 exposes P1 authenticated-RTT recovery storm

Real Normal/off Action39891326352 on source18860 (2% IID, 200ms one-way, near-MTU, 60s) has healthy host and Stop but UDP missing155/138 (2.63%/2.35%), TCP p99 7160/5632ms and backpressure. Probe RTT p50 is 400.3ms both roles while product outer recovery is fixed PTO80ms/W15ms. Each side has ~19k fresh records yet ~11.7k retransmissions and ~61k quota/capacity blocks. This is direct bottleneck evidence, not a seed search target.

One P1 ability batch now:
- genuine fresh unretransmitted authenticated reverse receipt measures RTT; SRTT/RTTVAR drives W=clamp(R/32,2..20ms), PTO=R+max(4V,2W,4ms)+10ms, Tcache=min(3s,max(2PTO+50ms,2R+100ms));
- bootstrap R650ms/V20ms covers the declared RTT600 core target until first authentic sample; no raw/RX-derived fake sample;
- a record pins bounded Tcache when first copied and still has at most two immutable same-PN/cipher repairs;
- local repair policy stays 10% fresh +32KiB sparse floor; only hard ceilings rise to 8MiB/direction and16MiB/process;
- feedback is bounded512 pages/3s, max8 pages/report and existing coalescing remain; replay is bounded100kPN/s,3s cache,650ms RTT,256KiB metadata;
- shadow stays4096. P2 must first eliminate/contain the current full-table refresh_rack_wakes before any65k expansion.

Native unit pins bootstrap PTO740ms/cache1530ms; authentic400ms sample learns W12.5ms/PTO490ms/cache1030ms and proves exactly two retries then expiry. After native+9MTU PASS, run one old/new Normal2pct AB only.