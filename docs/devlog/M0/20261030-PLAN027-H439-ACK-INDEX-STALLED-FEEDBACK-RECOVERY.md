# PLAN027 H439｜ACK元数据容量饱和后不永久饿死，免额外timer

复核原R2 `OuterAckIndex` 只在外层ACK上释放或被其他调用显式 expire；Linux/Windows原生worker接index后遇到长期纯ACK丢失，在24,576条容量顶端 `on_definitely_sent` 会永久返回false，后续再来真实新业务也无法登记可选Shadow。H439仅在原M4真实首次复制时、索引已满且最老元数据至少2s后 pop_first 一条，马上让当前已核范围记录继续入索引；先前Shadow有独立最长1.5s硬失效，此索引只用于可丢弃原密文修复缓存，不证明业务交付、更新Health、修改Auto或申请额外R/F额度。不会额外定时线程、全表扫描、单包内存分配；回归覆盖未满2s禁止驱逐、新来源单条恢复、旧ACK不伪造确认、同时计数容量严格2。未知反馈照样UNKNOWN。真实容量/高负载测量仍需PLAN027 A/B/C，不能写PASS。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Keep bounded optional first-send ACK index from permanently saturating after missing peer ACKs by expiring only one 2s-old metadata entry on next real M4 firstsend."}
```
