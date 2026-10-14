# 09 Normal与Game组合路径

## TX唯一处理链

客户端TUN/server业务入口首先完成原地址/会话归属检查，识别逻辑tunnel和真实payload活动；Game赋LogicalPacketID并加16B envelope，Normal保持原LINK内容。之后统一LINK fragment→可选FEC→按lane seal→ready发送。禁止每lane分别做fragment/FEC后再试图合并。

一个TX job携带不可变ActiveLaneSnapshot，不在逐包循环反复取全局mutex/sort lanes。snapshot已经按lane ID稳定排序，轮转起始lane索引使lane1不永久先发。对每个source：准备lane i密文后即可发送/加入ready，不能先构造4条lane全部密文才让第一条上网；批处理不能恢复这种屏障。

FEC block满时先发布最后一个systematic，再调度ParityJob。新systematic优先，但parity按其close/deadline进入受界队列；当两者都ready时按照配置r/k所需字节服务份额执行，避免不停新包把parity永远饿死。总输出跟不上时明确pressure丢弃，不挤大fresh队列隐藏问题。

固定off零encoder/zero FEC定时器；auto当前off仍可能有旧drain状态和最大FEC MTU包络，这个差异必须在性能报告中说明。高层控制策略不在逐包路径执行。

## Game慢lane和跨lane恢复

shared key=(logical tunnel epoch,direction,extended block ID)。每lane具有独立LaneKey、PN/seq、AEAD密钥和shadow。接收4份副本仍需4次各自完整性校验，但只一次logical decode/reassembly/delivery；不使用未认证头跳过解密，也不实现主/附属lane延迟解密复杂架构。

每lane有有界ready副本队列（按2ms服务量、最大8192slots且受总bytes）。满/不可写/无eligible budget时跳过这个lane副本并计lane_copy_drop，其他lane照发；不能为保住第4份复制停住前3份。健康capacity门要求该计数为0，过载时它是诚实退化，不算“仍完整4lane复制”。

RX必须把同逻辑tunnel的全部lane路由到同一个RX owner；它串行维护共同FEC/fragment和PacketID dedup，没有跨lane每包大锁。副本间不同shard互补，第一份有效source或恢复结果先到先交付。同一逻辑PacketID还要查一次delivered bitmap，避免一份从systematic、一份从FEC/另一lane恢复而重复业务。

共享FEC只减少公共编解码，不减少每lane必须的AEAD与wire发送；Amdahl公式按测得占比解释CPU收益。无流量不维持四倍轮询线程。

## Rotation与MSS变化

新lane须经过原真实TLS/admission、generation/key安装和原qualified条件，才加入ActiveLaneSnapshot。已有A继续承载，A+B阶段允许第一份成功交付；移除A之前B已能收/发实际有效控制/业务，不能把“创建对象成功”当qualified。

新B的MSS较小时：先在TX轮边界封闭旧budget的open blocks，已有旧shard仅发给能容纳它的旧lanes；新业务从新min budget产生新blocks给A+B。A排空/超过原有界drain后移除，不能要求所有旧大包恢复成功才能移除，也不能把旧大record硬塞B。

Game计划lane数是配置；rotation临时多一条必须遵守原max_active资源门和新总预算，不把无限重试新lane留下来。每个逻辑block的wire ID/profile不因某lane关闭重置。Normal rotation重叠期间同样不让新lane等待A未完成repair。

## 测试

一lane人工sleep/写EAGAIN不拖其他lane；四份到达顺序24种；source和recovered同时可交付；不同lane互补缺片；同epoch同block重复metadata、错epoch拒绝；2/4lane部分/全部黑洞；旧A有shadow但B已工作；新MSS变小；低档/off Game（若旧产品支持）行为明确。

正常性能锚点仍每方向逻辑3Mbps、Game2/4、FEC20:20；不偷换成每lane减少业务总量。分别报common FEC CPU、lane crypto CPU、I/O、copy/drop/queue age，证实“共享”实际发生。80s专项在优化后R6，不由本模块归因或提前关闭。
