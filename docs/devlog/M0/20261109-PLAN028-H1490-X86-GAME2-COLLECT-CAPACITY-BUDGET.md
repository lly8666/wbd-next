# PLAN028 H1490｜H1489双原始x86 Game2 ZIP验证收回；下一组L2/长测先做容量账

H1489 [纯离线Action42639985741](https://github.com/lly8666/wbd-next/actions/runs/42639985741) 真实SUCCESS，artifact13683558839 ZIP SHA256 `631d5cf144cb925153a8447ae93fb3cf767ecb4a833db26d1496b4777cb0ee88` CRC PASS；两份原本外层失败但原生真业务完整PASS的H1488/H1200 x86双物理来源ZIP准确核验 `OFFLINE_PASS_TWO_ORIGINAL_NATIVE_X86_GAME2_TWO_PHYSICAL_NO_NEW_NETWORK`，合格范围：Game2 Fixed6在同一443旁有Game4/Normal健康兄弟，物理IPv4与MTU双变化，各3代认证/两次exact owned old Stop；两次B各UDP16/16，两次健康兄弟每次80/80 UDP，唯一共享TUN final Stop。两份原Action FAIL维持，因外层报表后检查错误，未重测网络。H1484 ARM64五客户端零损与H1485 Game4 x86物理切换限定PASS继续复用。两条旧workflow均已移除push触发，避免再不必要重建。

下一独立阻断是L2容量与L3有限长测，不把H1461 600的75Mbps Alice DL32+server8-slot overflow45、1800的Alice DL351/queue overflow0混成同根。按样本30%×256B +70%×1024B算平均793.6B：50Mbps约7875.5业务包/s/方向，75Mbps约11813.3包/s；8条待发槽只容约1.016ms/0.677ms**业务到达时间**，未包含真实FEC符号复制、内核skbuff、调度停顿。H1360旧源75Mbps有效、宿主busy74.93%，H1459另源/另VM 75Mbps缺28、宿主busy90.03%；不同VM/源码不能证明产品回归或完全归因于宿主。应在当前source57b的**同一VM**做小而可判因果的50→75定向容量/CPU/实际TUN队列证据，50已经容量满则停止更重同族。严禁为刷zero-loss纯重复seed。另以本轮新认证交接修正后的SOURCE开展有限混合轮换长测；旧SOURCE66fb 1800原FAIL351不可覆盖。

无产品代码修改、无新增原生网络场景、全量H998与Windows L3/Android/物理限制原样保留，PLAN028 `IN_PROGRESS`。

```feature-impact
{"kind":"none","ids":[],"reason":"Collect immutable native offline qualification and calculate bounded next L2 load; no product/config/wire changes."}
```
