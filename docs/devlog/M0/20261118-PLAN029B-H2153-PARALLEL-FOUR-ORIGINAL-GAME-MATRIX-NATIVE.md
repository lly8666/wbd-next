# H2153｜Game2/4 × FEC off/fixed，四并行原Windows VM与20项真业务/Stop

最新H2152 SOURCE29074f2完成真实LAN物理UDP probe与完整签名矩阵源级门，四组未派实网：其变更没有native标记/CI接线。本次单独配置一种原生调度：`[plan029b-game-matrix-real]` 在现有原始Windows2025/WSL2 Workflow中**四个矩阵job同时**，每组执行固定五种 cold 配置 **off→all→LAN→普通CN→高级CN**，每轮原Go+Rust二/四条已认证TLS、原RustV4冷策略、OS Applied/内MTU/实际Wintun↔Linux TUN双向TCP/UDP、原Stop/WAL归位，严格同SOURCE/EXE/Linux二进制hash。默认外MTU1460，FEC off/fixed分组各自校验，Game2/4不跑旧028矩阵。

H2152 Fixed原夹具只承认`advanced_fixed`而将其余四项`*_fixed`错误拒绝；现全统一`p029b_game_policy=tag.removesuffix('_fixed')`，完整校验fixed/off分支并不改变真实用户业务配置。LAN probe是 **Windows真实 Wintun UDP → Linux eth0:46117**，原Linux核 socket严格回验原Windows物理源IP，随后两端原Stop；不用Windows裸物理UDP代替Wintun。普通CN物理DNS真A→同全球海外IP走Tunnel、高级CN FakeIP Direct UDP+32768B TCP/half-close及Tunnel双向TCP/UDP，未成功不生成PASS。

签名 Action 失败时按第一个真实case修，仅重派相应独立SOURCE场景；此处未声明20项PASS。Rust TCP/FEC/repair/wire热路径均未改。
```feature-impact
{"kind":"none","ids":[],"reason":"H2153 only wires four existing original Windows Game2/4 policy native suites to independent parallel job matrix, completes true LAN Wintun→Linux physical probe and exact source safety checks; no production runtime or feature semantics changed."}
```
