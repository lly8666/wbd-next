# M0 / R1 首包优先：真实worker身份、独立测试、buffer交接与M4有界stop

2026-10-14。用户提交对G2交接`8c1ab7254941fbeb9d495fb838f7bf8fc3953130`的四点复核意见，M0接受并落实可验证的主线边界。任务不变更role revision2/epoch1，不启用生产V4，不将旧fake通过认定产品。

**why_now**：先前G2分支确实存在且Governance绿色，但push event的`inputs.role_id || 'M0'`将worker的workflow身份、continuity和收据归成M0；旧G2`1 passed`及platform`7 passed`未筛选范围，worker扩展后的新测试可能使老suite误红。types又缺跨角色唯一byte所有权API，真实路径容易增添全包复制；platform R0 harness在驱动借用时Mutex、Arc及Vec并且`wait_drained()`无截止时间，不能拿来作为生产热路径。

### 改动与分工

1. M0在`governance.yml`调用`tools/worker_scope_ci.py`，每次基于**实时main registry**与精确`GITHUB_REF_NAME`解析唯一role；对worker分支从`G2_BASE=83bd720368b9be68b3c4c94d7462d20cf4d796db`到SOURCE**逐commit**检查路径、父数，main整合祖先提交排除，但worker自己的非法修改/越权role/epoch/revision/分支拒绝；在`GITHUB_ENV`为后续审计/manifest固定真实role。角色身份成功不代替worker S/H连续性；首个checkpoint=null会诚实保留BOOTSTRAP_RECOVERY_REQUIRED。新增Python负例覆盖M0冒充M1、越路径、未知归属和非M0合并。
2. R0 G2 wrapper只执行`--exact tests::bootstrap_is_not_product_qualification`固定脚手架；R0平台fake wrapper只执行`r0_`开头的老7项并精确匹配名称。新`worker-native-tests.yml`仅worker分支自身源码变动触发，编译对应单crate一次、独立consumer核源码/二进制SHA256，必须有**至少1项真正R1（M1/M3/M4）或R2（M2）名称测试**，没有则不能标通过。不能放宽R0计数代替新测试。
3. 新`wbd-types::buffer_contract`仅定义`UniqueSealable`/独占可写、`FrozenRecordHandle`/不可变拥有句柄、`DriverRead`只读借用和arena+generation的身份。M1拥有arena+return队列（第一次写实现验证clone不复制payload）；M3将真实AEAD/HP就地Seal并消费UniqueBuffer；M2 clone handle复用旧密文；M4 driver readonly+async kernel lease。原始mock实现仍有Arc与一次Vec复制，只用于trait类型单元测试，明确不能称零拷贝/生产性能路径。shared types不跨C ABI。
4. 旧`crates/wbd-platform/src/lib.rs`只是R0 fake proof，**禁止**直接用`BorrowFence::wait_drained()`无界堵关机、批次每次Vec重分配、每借用锁+Arc的慢路径作为生产资格。M4第一真实实现必须：预分配批次结果/复用ring；owner额度/return backlog预留；原生send已同步复制或async借用至completion; 单调时钟deadline到期返回`DrainTimedOut{outstanding,...}`并保留尚未完成内核lease，不能假清零、不能free；稳态不得每包Mutex争用，每例以native job和deadline/stop race测试。M0只立接口/验收，不越worker边界代写M4。

### 第一条真实业务验收定义

**R1 Normal/FEC off 一包 TX→RX** 必须证明：来自一个真实输入业务字节串进入M1 owned缓冲；M3以真实Rust已认证record seal（PN消耗），LINK普通包无额外20B头，FEC disabled，M4真实/限定native传输接口捕获wire，再由M3真实open认证并向M1发出payload delivery；同一批固定SOURCE/run/job的日志有原文hash、wire bytes和PN/seq、buf handle代数、零拷贝/分配计数、zero unauthorized fallback，且业务成功必须由**真实Rust**执行，不能用fake crypto/mock driver拼成产品PASS。驱动初期in-memory loopback只标`IN_PROCESS_ONLY`，不冒充Linux/Windows真实设备。此后再接旧Go控制入口（V4仍fail-closed直至产品资格）和FEC/R2/R4。未跑的Normal/off业务端到端仍`NOT_RUN`。

**done_when**：GitHub Actions在新main SOURCE的role推断与负例、旧R0 suite精准计数、共享Buffer契约Rust编译通过；然后精确同源fast-forward每条未开工worker分支，能看到真实M1/M2/M3/M4`role_id`的Governance产物。真实worker新测试只有各自提交后才会PASS；M4性能替换和Normal/off不是本次假装已交付的scope。

**唯一下一动作**：四个worker分别在自己的分支第一个S/Actions/H——M1真实arena/owner，M3先FrameBudget与crypto seal/open，M4限定native driver/有界stop，M2 receipt纯状态；M0串行接好真实Normal/FEC off首包并用同一SOURCE的回归证据决定是否进R1 qualification。不要继续优先添加抽象证明链条或性能形容词。
