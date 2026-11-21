# H2274 · Normal FEC2 在弱网真实 TCP 的最小差异试验（2026-11-21）

**待验证问题**：现有Linux ARM原 Go TLS/Rust双向200ms、1%/5%真实内核丢包时，客户端SharedTun满丢0。H2270证明外层ACK/SACK机会式原密文修复可实际发出R>0，但5%开启后吞吐和P99均未证明改善；H2272测得旧回显服务端Nagle使小TCP P50/P99显著变差，排除后5%小TCP P99仍1407ms、四bulk实际接收约38Mbps。内层TCP_INFO显示重传/RTO，意味着本机队列不是唯一主因，也不能仅扩SharedTun或FQ cap。

**可改变决定的对照**：已实现的原Normal FEC2是当前能在收到TCP反馈之前恢复丢失原内层DATA的独立机制。现行FEC2理论模型（满k=16、独立IID符号丢失）p=1% light(16:2)每源未恢复q约0.012309%，p=5% mild(16:4)约0.066180%，相对无FEC降低损失但多12.5%/25%名义冗余、编码CPU以及partial-block和MTU开销。真实数据不服从该理想，可能仍无效；固定下发不构成默认修改。

**实施**：本分支只为测试夹具增加显式H2274 FEC对照枚举。Linux ARM64独立1%与5%各一Action，当前非probe原Go TLS/Rust、真实raw/TUN、三netns、四内核TCP bulk+160TCP/UDP回显、双向200ms原内核netem、同一runner A Normal/off→B 原生Normal/fec-fixed profile0(1%)或profile1(5%)→A′ Normal/off，同release二进制hash与Go冷TLS、内核数据路径完全相同。三段原外层机会修复都经Rust原回执验证OFF，测试回显server/client的TCP_NODELAY均启用，真实路由/MTU1200外层1160与既有FQ600不变；FEC源本身有额外头部和更小内层MTU，应计成本而非视为算法净提升。B必须从原Rust Go连接有实际`V4_PUBLIC_FEC2_READBACK`固定档profile读回，不以CLI字符串冒充FEC已生效。三段各保留TCP retrans/cwnd、有效接收Mbps、CPU/有效GiB、小TCP P99、UDP未回、原Stop和CPU/字节成本。完整窗口外层FEC线路放大/真实k分布需结合原本FEC TX/RX计数再作产品决定。

**改判条件**：B相对A/A′若提高有效吞吐、减少inner TCP retrans和小TCP晚回且资源额外代价合理，则进一步检查双端FEC recovered TUN/实际block和Windows Normal同源适配；如果CPU代价高/尾时延继续坏则保留off，转而定位TCP_ACK方向和真实netem/MSS，不扫描随机队列/FQ参数。两架构与Windows/物理未验，全包OPEN。新增product代码0，默认及安全硬门不变，执行前结果NOT_RUN；所有旧失败与SOURCE不覆盖。

```feature-impact
{"kind":"none","reason":"H2274 test-only original Normal/off vs already-implemented FEC2 fixed light/mild native A/B/A' harness; no product code, CLI default, driver, security or Stop change."}
```
