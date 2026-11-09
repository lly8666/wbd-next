# PLAN028 H1480｜服务端 B 等对端真实M4 RX后发布下行/退休 A（冻结期缺陷修复候选）

原 H1478 SOURCE66fb x86同VM真实five-client rotating12 Alice DL永久缺10；两侧64B外层物理包头两次窗口合计114,967 DATA匹配、观察者kernel drop0、server共享TUN队列0；服务器新一代Rust本地START即发布 /32、Go立即Stop旧代，而客户端新一代必须等认证后的反向M4真实收件才发布自己的TUN入口。**这是契约缺口，原始FAIL保留；该修复能否治愈丢包必须真实触发回归。**

最小两端冷接线：Rust共享TUN同租约存在活A时，无论Server或Client，B仅prepare+RX worker/Tx owner而不发布新发送路由。客户端B在已配置OS MTU/租约、已真实attach原RAW RX+启动M4后，沿现有原密文AEAD Health kind0 立即发**一次冷就绪通知**（不是业务数据、不是稳态探针/新wire类型）。服务端B只接受这一新generation已鉴权kind0（不把纯上行、ClientHello/TLS或RAW ACK当接收就绪），再原子发布新 /32，之后才通知Go rec.ready并严格owned Stop旧A。B失败或5s窗口未证：清除B过滤映射并Stop仅B，A原路由/生存位保留。首次服务器/客户端无活A则无需新证明、直接正常启动。Game成熟数据面/固定FEC/Auto/record/MTU规则不重写，外层原密文repair/FEC/复制均不动。现行server cold receipt(3次)与新client cold reply(1次)均复用同一合法kind0，只有换代冷路径增量；不加Go逐包反馈或定时固定热泵。

**L0确定性单测**：旧A真实shared route不被server B本地start/普通认证上行取代；只有本B已验证客户端kind0才能切路；旧A精确retire不毁B；客户端仅B发一次冷Health后恢复正常timer，首代不额外发送；Go有约束的阻断/正反例。保持验证键/PN/generation/原密文/Stop。修复候选未跑不写PASS。

**L1有限真实验**：下一个Linux完整平台按x86→**原生ARM64双端**交替，一Action一个180s五客户端rotating12，Normal Alice 12Mbps，另外四兄弟2Mbps，原UDP/TCP混合、双轮换、外层默认1460、源锁manifest原Go版本+ISA-L hash、所有六owned Stop。不能用静态无轮换PASS给此条件修复过门；必须server B deferred和两次AEAD client proof及B原生路由promoted，所有双向unique UDP不能失/重。性能台阶12Mbps约~1.9k平均UDP pps/方向（混合长度实际见夹具）；不重刷seed。若编译/夹具错误离线或该批最小修复；若业务依然缺失，留FAIL再走细粒度RAW/socket证据，而不是重复扩大双发、缓冲。

构建/Action [H1480 workflow](https://github.com/lly8666/wbd-next/blob/main/.github/workflows/m0-plan028-h1480-arm64-client-ready-fence.yml)随源码同次commit触发，代码还未验真。原H1479证据不改。功能范围不添加配置或UI，仅修§2就绪/交接硬门。

```feature-impact
{"kind":"none","ids":[],"reason":"Frozen PLAN028 correction to existing authenticated generation handover, no new user-facing configuration or transport wire format."}
```
