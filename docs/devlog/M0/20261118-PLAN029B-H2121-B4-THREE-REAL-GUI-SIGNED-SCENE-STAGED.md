# PLAN029B H2121｜B4原WinForms三代真实连接/Stop单场夹具与签名门（SOURCE待验）

本批按H2120 cursor接续，仅为B4补原签名Windows2025 Npcap/Wintun↔WSL2测试接线。此前 [H2120真实Go/Win/Linux Rust纯三代PASS](https://github.com/lly8666/wbd-next/actions/runs/44124045844)，其真实GUI三代仍NOT_RUN。保留H2115/H2117/H2118原失败及H2112 /128 IPv6限域PASS。本批没有改Go/Rust产品热路径、FIN/WinSock公平性、FEC/repair、外层wire和旧WFP。

新增 `tools/m0_plan029b_b4_real_gui.cs` 经原 `m0_plan029_gui_real_bridge.py` 同源编译，真实 `MainForm.SetEditor/SaveEditor/Connect` 三阶段高级CN `true`→普通CN `false`→split=false/all。每阶段原Go `--check-config`、原Go/Rust独占Wintun OS Applied、Windows kernel UDP DNS A与业务回声、完整原GUI断开/OS WAL Stop；只有首代原生FakeIP，经真实旧应用缓存向第二/三代重新发包，不把缓存未收到回复替代包已进入Rust的证明。首代完整Stop后由同一外层原owner CAS移除TEST-ONLY物理`203.0.113.77/32`，第二/三代相同真实A经Linux自有TUN Tunnel交付。原FakeIP journal保留，停用代不改写；每代 `ipconfig /flushdns`，不动宿主全局IPv6。所有外部临时IPv4 alias/route原finally回收。

同场原WSL2 `tools/m0_plan029b_b4_guest.py` 在真实`eth0:53`和`wbdwl4:53`各单DNS socket、真实`203.0.113.77:46119`应用socket与两个Linux AF_PACKET只读入口记录物理/隧道lane，拒任何旧FakeIP UDP marker/198.18真实出口，绝不留大pcap。新增 `verified_plan029b_b4_three_gui_child_mss` 严格核验3个原Go TLS子进程、Windows SYN字节/原Linux SYNACK、原M4 3次接纳和1460/1389；B4旁路旧H2066双代校验但不放松任一已有原保护。既有Normal原生两OS TCP/UDP双向、原Stop和源锁产物检查保留。

原Windows/WSL2 `.github/workflows/m0-wl-public-normal-full.yml` 单显式`[plan029b-b4-gui-three-real]`门，仅选Normal/1460/B4，不选旧029实际Direct/P2/028场景。包含源码、bridge、MSS和静态独立廉价检查；新增的真实检查必须依次完成后才会生成PASS marker。无V2伪Ready、无Go逐包或自定义IPv6组件；不制造资源/性能增益百分比。

**本次记录为源码候选：签名B4原生Windows/WSL2、真实Linux出口、原WinForms 3个Applied/Stop、旧FakeIP不外发、Game2/4、B5同VM<=10Mbps CPU/GiB+RSS+唤醒+p99均NOT_RUN，禁止用纯测试PASS冒充。** 成功且核对原ZIP/SOURCE/hash/CRC后才补真实evidence并升级功能卡；如果首个真实FAIL，按异常路径只修一因，不刷seed。029B及029 OPEN，030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"H2121 only stages B4 source-locked original signed WinForms/WSL2 three-generation test fixture and CI; no product runtime changes, network result pending"}
```
