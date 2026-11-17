# PLAN029B H2125｜首个真实 DNS 上游事务 ID 已被原 Rust 改写，修夹具不改产品

[原 Action44144504089](https://github.com/lly8666/wbd-next/actions/runs/44144504089)，SOURCE `c0f5cdf2610cbfb6c103bc1cf51bf1c949f47314` **FAIL**。下载 ZIP `14356372886` SHA256 `4252f580f5dd9f88ca2491f01f4906268e9943611f70f98760fb8a5a5e4c9e68`，26条 CRC 全PASS；报告的Linux/Win产品/夹具 SOURCE一致。真实 WinForms Gen1 OS Applied/Ready/Wintun MTU1460/inner1389、Windows↔WSL2 双向 UDP、1个原始M4会话通过；DNS收到 SERVFAIL(2)/ANCOUNT0；失败路径原Rust Stop和WAL恢复真实PASS，后两代全未运行。

**唯一首错已确认：** 原 Linux 物理 UDP53 客户端从 `172.22.64.1:63278` 收到目标CN原问题、QTYPE A、RD=1、QDCOUNT1，所有真实来源/类型均正确，但上游 DNS ID=`0001` 而 WinForms 应用原ID=`2961`。原Rust DNS转发使用独立上游事务ID；夹具把二者强制相等因此抛异常，没有返回真实 CNAME+A。修法仍要求源地址、物理/TUN、精确 QNAME+QTYPE、三代业务和 Stop 顺序不变；回复回显真实 upstream ID，Windows GUI 独立校验恢复后的 app ID，不以文件里的号码冒充真实应用。

[H2125 SOURCE4fe9](https://github.com/lly8666/wbd-next/commit/4fe9cdd27a6c14df7e31e7b4285c7b30dadf1f22) 原生预检 [Action44147216905](https://github.com/lly8666/wbd-next/actions/runs/44147216905) **FAIL_BEFORE_NATIVE**：源代码额外增加“先 DNS 后业务”检查，但静态测试仍匹配旧 `if peer[0] != expected` 字符串。H2126 [SOURCEcb40](https://github.com/lly8666/wbd-next/commit/cb40f28ea70789baaab6549ea3cf084f22f2decc)仅同步该断言，新 [Action44147461765](https://github.com/lly8666/wbd-next/actions/runs/44147461765) 收集时未最终结束，**不可宣称 B4 PASS**。B0–B3历史限域保留，Game2/4、B5同VM10Mbps、029B仍OPEN，030未开。

```feature-impact
{"kind":"none","ids":[],"reason":"H2125/H2126 only B4 original WSL2 DNS upstream ID test fixture and exact static guard, no runtime Go/Rust/GUI/product semantics modified."}
```
