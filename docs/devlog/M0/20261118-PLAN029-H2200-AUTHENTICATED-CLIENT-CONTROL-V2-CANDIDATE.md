# H2200｜加密配置往返随机尾部 + 客户端选择驱动Linux服务端（代码候选）

原V4 TLS13成功后才写 Admission request/reply，末尾24B extension 的 [23] 旧值必须0，原Reader只读固定长度；裸append随机会在Go→Rust Detach之前留下无法解析的控制字节。改为version2明确边界 `BE16 length + 32..500B crypto/rand`，每向各独立生成、同原TLs加密application write、一次request/reply，无TLS前包/伪扩展；V1原解码保持off、V2服务端原样回显客户端off/tls/flows并绑定TLS exporter后才生成验证cold snapshot。Linux Normal/Fixed/Auto与Game2/4原Rust owner全部改为读会话而非服务端CLI；Game所有lane一致、单lane换代不得擅自改模式。服务端全模式可独立有界填充；FEC parity及控制本身不进热路径填充。

新增真实Go TLS三档、V1兼容/损坏长度/熵不足、两向变长与不残留解码单测；Linux x86/ARM每ISA12个真正客户端/服务端原场景，在客户端tls/flows时故意让server本地off，客户端off时server本地flows，验证server真实Rust M4 copied模式匹配以及双向kernel TCP/UDP/Stop。现在仅 **CODE_CANDIDATE/NOT_RUN**，尚无新SOURCE签名。先前H2197真实20/20签名不借用。详细[协议决策](../decisions/M0-PLAN029-H2200-PROTECTED-ADMISSION-PADDING-V2-20261118.md)。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2200 new encrypted protected V4 TLS Admission V2 per-client off/tls/flows echo and bounded independent random suffix in both request/reply, old V1 off preserved, 12-case dual native fixture candidate NOT_RUN"}
```

首次SOURCE `a22ab7fd` [native Action44303725701](https://github.com/lly8666/wbd-next/actions/runs/44303725701) 双ISA预检 FAIL，停在老静态测试 `assertIn("server_padding_records",cases)`；H2200新增控制回归把server+client统一成 `row.get(role+"_padding_records")` 迭代，原字符串不再出现。维护回归 [44303725767](https://github.com/lly8666/wbd-next/actions/runs/44303725767) 同一个静态断言FAIL；治理/Feature [44303725803](https://github.com/lly8666/wbd-next/actions/runs/44303725803) SUCCESS。仅修测试断言匹配真实代码，不变协议/产品或伪造真网PASS；原失败保留，后续新SOURCE单次原生重测。
