# PLAN028 H1479｜真正触发同源12Mbps换代缺包，但114,967个外层真实DATA包完整到达客户端物理口

复核 [H1478 Action42619474139](https://github.com/lly8666/wbd-next/actions/runs/42619474139) SUCCESS、原始artifact13675097130 ZIP SHA256 `567d281542f2ac96f577a7a85ba9af11009fedc77efcf427b750388ecf8b4ee1` CRC_PASS、SOURCE66fb SHA构建清单；同VM x86/x86真实5client TLS→Rust RAW/TUN 180s rotating12，真实业务及所有6 owned Stop。Action是有效测试执行PASS_SCOPED，业务Alice下行UDP独立ID **FAIL永久少10**（36.97–36.99s共7，135.39–135.40s共3），不是修复PASS。

两侧物理AF_PACKET捕获各32s、64B包头仅在RUNNER_TEMP，原始文件销毁，边缘各1s剪去防启动/收尾偏差。第一次旧41031有15306份、B56872有42196份，全部发送物理见→客户端物理见；第二次旧56872有29501份、B64791有27964份，也全匹配。**合计114,967份内窗外层DATA匹配0缺**。两端tcpdump packet dropped by kernel均0，不是观察者丢包造成零结果。原server共享TUN Alice offered331513/direct331513，pending_peak/overflow/retired/age/full均0；client gen2 raw_observed188525、gen3 85468，AEAD重放/输出失败0；各代500ms服务器末采样 m4_copied为188533、85473，但时间轴不严格对齐不能用8/5直接等同业务7/3。

**代码契约差异**：Normal客户端B需要真实收到server AEAD/Health才能发布自己的TX TUN；server新B在本地Rust M4 Start就直接替换服务器同租约 /32 下行TX，Go立即Stop旧A，**未等客户端B自己的原生RAW接收就绪证据**。缺包对应客户端B冷TLS约36–44ms原生安装窗口；这是可行根因假设并且当前就绪契约真实非对称，但物理匹配不等于Rust socket读入，也不等于server每个内层包确已封装。下一步以现行双端认证Health kind0/原generation证据建立服务端待发布屏障，先L0正反例；客户端B就绪需一次既有合法、经AEAD验证的冷收据，不能TLS local READY、TCP ACK或无源定时冒充，不能新steadystate wire、双发或增加队列。对照过载75Mbps另故障域。

本回写只记真实物证、不修改产品或重跑原样本。PLAN028仍IN_PROGRESS，原失败/Windows L3 NOT_QUALIFIED/H998/物理 Android NOT_RUN保留。下一Linux完整平台优先ARM64。

```feature-impact
{"kind":"none","ids":[],"reason":"Original-source triggered network evidence and causal source review; no user-facing behavior or product code changed."}
```
