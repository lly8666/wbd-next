# PLAN028 H1548｜用户新验收范围：一个真实Windows＋四个Linux，200ms双向250–300Mbps持续600秒

更新用户范围：不再要求五个 Windows Wintun 在**同一 Windows OS**并行。新基线是**1个Windows2025签名Npcap/Wintun Alice Normal-Off ＋4个独立WSL2/Linux netns** (Bob Auto, Carol Game2, Dave Game4, Erin Fixed6)，共用一个 original Go/Rust TLS443 Linux shared TUN 服务端。五真实账户独立凭据、内层/32 lease、TLS/AEAD/epoch/M4/Stop均不降低。旧五Windows原始FAIL保留为历史，不再阻碍**用户新定义**验收。

源码 SOURCE `7370d2bc6c4ad5963e735d2c885df8edb7fec7a9` 只新增 H1548 测试装配，无产品Go/Rust协议变更：
- Windows原已通过的 H1415 bridged WSL2 with one signed Wintun and one Linux netns真实OS拓扑复用，扩成四个独立 WSL Linux netns/veth；各Linux客户端启动原 original Go TLS + Rust TUN，Windows只启动**一个**原始Wintun。
- 原H1506 Windows↔WSL eth0入站IFB+出站 443–446 qdisc真 200ms/0%或30%，四Linux各在实际veth两方向设置相同netem，非生产协议参数；十个物理方向内核tc `Sent bytes/drops` 每10秒读回后**只算Windows真实eth0上下行＋四个Linux各一组物理veth上下行**，不重复计算路由、FEC副本或业务计数。
- 0%内层基础每方向 `8+14+11+6+9=48Mbps`；30% `10+22+18+10+14=74Mbps`。同规模先前Linux原始实际外层333.930Mbps@60Mbps/way和304.271Mbps@82Mbps/way，粗外推约267/274.6Mbps，仅作本轮初始负载选择。混合 Windows/WSL 的真实吞吐未知，以新的10秒物理计数为准，试验倍率有界0.65..1.35，不靠事后调验收门槛。
- 五组独立真实UDP 256/1120B、真实双向 framed TCP (Windows与Linux OS分别 bind 各自/32)、600秒共同开始、十毫秒唯一收包窗、真实Linux原生 M4 cohort与Normal代；Windows原有Stop/WAL、四Linux原进程和一Linux服务器 Stop；host本核CPU/RAM持续30秒容量阻断、原 L2/WSL管理路由/网桥/密钥严格owned cleanup。脚本失败不得把原始程序未启动冒称 FAIL 产品。
- [Action42852209993](https://github.com/lly8666/wbd-next/actions/runs/42852209993) 两个独立Windows VM（loss0/loss30）共享一次同源Linux产品编译；cheap新source contract与默认装配 **PASS**，当前 Linux Rust/Windows Go Rust prereqs 建构中，真正600s **NOT_RUN**直到两个Windows jobs开始网络。
- 原旧 H1547 Linux-only 0%、30%双向 300–350Mbps **PASS_SCOPED**原证据不变。当前混合场景不触发H1506四次Windows物理源IP事件，因为桥接WSL操作与原owned alias physical event尚不可直接同场复用；本轮该轴明确 `NOT_TRIGGERED`，不能伪称物理 source-IP reauth PASS。原 TLS计时轮换、实际Game M4仍照验。
- PLAN028仍 `IN_PROGRESS`，Android/物理WAN/ARM64最新源码五客户真实长测不在这两个Windows2025场景自动宣称完成。

```feature-impact
{"kind":"none","ids":[],"reason":"New source-locked Windows1 plus Linux4 mixed native real network stress fixture and Actions, revising acceptance scope per user; no product feature, Go/Rust protocol or default option changed."}
```
