# PLAN028 H1459｜四路源548真压测，三项范围PASS＋Normal75真实FAIL，历史 CI 误标

用户要求一次多路并行含压测。SOURCE548a真实Windows+Linux 600s仅约9.3pps，故H1458一次使用已核对的同SOURCE Linux原始Go TLS443/Rust ISA-L构建、四台独立ubuntu-x86，每台5个真实账户、6 Linux netns/OS TUN/UDP/TCP、180s + 六原生Stop；Action [42567898270](https://github.com/lly8666/wbd-next/actions/runs/42567898270) 四场网络jobs和预检**全部SUCCESS**，对应四个独立已下载CRC核验artifact。原GO/Rust产品本次没改，所有速度是实测业务Mbps，非仅目标值。

逐项复判：
- Normal50实际Alice双向50Mbps、五客户端单方向合计58Mbps、CPU41.26%、UDP无缺失且所有server lease队列0溢出，`PASS_SCOPED`。
- Normal75实际Alice双向75Mbps、合计83Mbps、host busy90.03%、最大core90.36%，**Alice上行UDP发送1099425/接收1099400（缺25），下行发送1099423/接收1099420（缺3），零配置物理丢包总共缺28；服务端Alice租约`pending_overflow=5`、peak8包，`offered=1402924` `direct_delivered=1402889`**。旧专用h1360审计并未将这类零损真正丢包/queue overflow算入最终门，尽管raw rapid已有`SERVER_PER_LEASE_QUEUE_OVERFLOW`告警，反而给`PASS_SCOPED`。这必须被独立重算为 `FAIL_SCOPED_ZEROLOSS_UDP_MISSING_OR_SERVER_LEASE_QUEUE_OVERFLOW`；不把绿色Action当产品PASS，亦不能在90%host busy时武断归因为产品某个线程；对照要在同VM/同源做A/B才能推因果。
- Game4 Fixed6实际逻辑20Mbps双向峰值30s，五客户端合计28Mbps/方向，host busy46.45%，零丢零队列溢出、回落10Mbps持续60s，`PASS_SCOPED`，无L1真实轮换结论（轮换计时器停在600s）。
- 五模式混合弱网含Erin配置30%/125ms，真实内核qdisc drop uplink29.9313% downlink29.8350%，原双向UDP/TCP + 5客户真实轮换+six Stop `PASS_SCOPED`，rapid告警0；配置30%的真实丢包是预期，并不适用0损全部不丢要求。

**历史参照不隐瞒**：旧SOURCE6c5 Normal75 original [42441021254](https://github.com/lly8666/wbd-next/actions/runs/42441021254) 原artifact13600784818零包缺失和零queue overflow，host busy74.93%；旧6c5与SOURCE548 Linux三组件二进制哈希都不同，VM也不同，**尚不能证明版本回归或特定产品队列算法缺陷**。修改测试夹具路径时还触发旧H1349 Game4 [42567898293](https://github.com/lly8666/wbd-next/actions/runs/42567898293)，原ActionFAILURE保留；其原始网络峰值20Mbps、Stop/审计`PASS_SCOPED`，只因工作流最终断言仍写“3_5_10_5”而非“3_5_10_20_10”。这属于 harness result-enum 错误，不重跑、也不修改历史Workflow去意外触发再次原生网测。

H1459新增**完全离线的独立Linux读取** `.github/workflows/m0-plan028-h1459-offline-rejudge.yml`，只下载四个SOURCE548及两个旧SOURCE6c5 Action已存在的原始zip，逐客户端+方向重算真实UDP缺包与server lease pending溢出，核对原始六Stop和CPU/峰值，自动将零损异常判FAIL_SCOPED、保留其他范围PASS并输出源锁JSON。新增unittest/压测审计代码只改离线result gate，**不重派任何网络、无产品/协议变更**。本证据中的离线Action在commit前仍为NOT_RUN，不能预先宣称其PASS。旧GitHub-hosted Win1800 L3仍NOT_QUALIFIED，ARM64两次1800和Win600各自PASS_SCOPED，H998历史FAIL和Android物理NOT_RUN留存。不做029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Offline immutable original source locked pressure ZIP rejudge; strict zero-loss UDP/queue accounting, historical false enum analysis; no product changes or new native network."}
```
