# PLAN029 H1868｜复用本项目已写小额度Direct资源压测，修真实入口

- 既有`tools/m0_plan029_h1778_windows_bounded_flow_pressure.py`与Linux独立物理socket+TUN收件夹具，在**真实签名**Windows Go/Rust/Wintun Normal v3，冷配置`--direct-flow-hard 8`：同时尝试16个Direct UDP tuple（不能超过8个真实回声），再建新Tunnel UDP（真实回声）、保活原Direct每12s到127s，超120s空闲的其他资源释放后新Direct恢复、老Direct仍回声；Linux分别检查物理Direct源与Tunnel租约，无VM-wide内存耗尽/无限刷seed。
- 旧H1778当时前置H1775 DNS listener首错挡住本子项，`hard8 pressure NOT_RUN`真实记录保留。后续原H1864一场包含DNS/物理Direct/Tunnel TCP/UDP完整已通过，但新`[plan029-v3-real-direct-pressure]`仅在workflow`WBD_PLAN029_DIRECT_PRESSURE`存在，没有进入`tools/m0_native_ci_scope.py`显式授权，且V3 ABI/Direct/outer1460/TUN1460环境没有同marker，存在Action绿但未真跑或构建错误风险。
- H1868只同步此一marker的4处现有source-locked场景选择器、native scope+纯test，保证同一SOURCE构建`m0_v4_probe`和原1460外层/WSL TUN MTU。一个Windows VM仅一个Normal压力场景；不带P1/P2/IPv6 marker，不复跑旧028矩阵。
- 完整压力退出仍不等于8 UDP成功：TCP共享buffer压力、DNS事务/缓存/FakeIP满额及RSS/最老队列年龄必须分别证明；此子项只验证**Direct hard8、现存Direct和新Tunnel相互隔离及到期恢复**。typed capacity原因需另外计数，不把未回复16个Direct全部推断为硬满导致的丢包。
- 新H1868完整原生Action在提交时NOT_RUN，先读cheap/编译/实际第一异常与原finally-owned Stop，不伪造资源性能。H1866 IPv6与H1867 P1当前在途独立SOURCE，先收并保留失败。029继续IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Wire one bounded true Direct-hard8 vs new Tunnel/old Direct/idle recovery signed Normal resource pressure scene through existing native scope, exact V3 ABI and MTU, preserving all old exits."}
```
