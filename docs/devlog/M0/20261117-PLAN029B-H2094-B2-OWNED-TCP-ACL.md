# PLAN029B H2094｜B2真实DNS/共享CDN先达成；TCP45902首错定位到夹具owned ACL

H2093 [Action44068272525](https://github.com/lly8666/wbd-next/actions/runs/44068272525) / SOURCE `5327acf268f49c6edc860400bfab2e12d381fbfc` 签名 Win2025 Npcap/Wintun↔WSL2 原产品、原二进制构建/Go/Rust编译均PASS；原ZIP artifact14321499645（sha256 `b07f419975a6a3df60a7c53b3300d8b65011aa7275c0fb86c35252b8c59d87bc`）。本次B2真实DNS验证与H2092不同，**两个出口均各收到唯一有效请求**：CN物理直连DNS返回CNAME/真实A `203.0.113.77`/TTL2；非CN在Tunnel DNS返回同一真实A，二者Windows应用各自UDP业务都走Tunnel，Linux无物理业务包。原应用回执为**B2功能阶段PASS_PRE_STOP**，不是完整产品验收。

完整native Action仍 **FAIL**：B2后的公共TCP双向回归中 Windows→Linux 有真实回显，Linux→Windows `203.0.113.77→10.66.0.2:45902` 超时（Windows监听端收到0），产品owned Stop未执行为PASS。精准根因在**测试自有**入站Allow：工作流只给既有029 Direct、Game4和P1源 `203.0.113.77`；029B B2遗漏，退回只允许 `10.66.0.1`，而这轮Linux原内核客户端按已有固定源绑定`203.0.113.77`。双方源码不做TCP栈修改、也不删除全双向检验；仅把B2选入原精确单源/单本地IP/45902 owned规则，继续校验读回和finally删除，新增静态回归防再遗漏。

下一次H2094按相同`[plan029b-b2-cn-ordinary-real]`唯一signed场景验证；**本次新SOURCE未出结果记NOT_RUN**。H2091/H2092/H2093 FAIL不覆盖，B0旧source限域PASS不移植成新SOURCE。高级CN、真实IPv6、GUI生命周期、同VM10Mbps CPU/p99、Game仍需要独立证据。保持029B计划不重开028/030。

```feature-impact
{"kind":"none","ids":[],"reason":"H2094 edits only test-owned signed Windows TCP45902 source-specific firewall fixture regression; production ABI, Rust data plane, Go GUI and feature semantics unchanged"}
```
