# M0｜PLAN029接续提示词

**前置交接（H1657，2026-11-12）**：PLAN028 已经用户授权作限定范围收口（非全L3/ACK/GUI真实起网PASS），[H1657权威证据](../evidence/M0/PLAN028-H1657-USER-AUTHORIZED-SCOPED-CLOSEOUT-20261112.json)。此文件是供**新 agent**启动 029 的入口，不表示本次028收尾已替用户自动激活029。新 agent 接到启动指令后，先核 main/registry/cursor，再按 M0 单写者约束转换任务；直接复用经证实的 028 配置/MTU/会话接口，不重刷旧七模式。ACK未解、独立Windows L3与真人GUI签名起网未测不等于029依赖已有PASS。


跨包红线：先读 `docs/architecture/TLS_HANDSHAKE_CONTRACT.md`；预共享route-key可导入/手填，本地生成/存储/验证，不得为配置便利恢复TLS前私有交换或关闭服务器验证。

你继续lly8666/wbd-next的PLAN029。读START_HERE/AGENTS、M0长期提示词、实时registry/cursor、`docs/decisions/M0-LEGACY-ROLLOUT-20261102.md`、`M0-PLAN029-CLIENT-DNS-PADDING-20261102.md`；只补checkpoint后相关增量/Actions，先收已有结果。文件存在不代表已启动，用户调用本提示词后按现有机制登记任务。

目标：Windows客户端服务器地址支持IP/域名，DNS接管后仍能重连/唤醒/换lane；配置落到真实CLI/GUI/owner；有限TCP/UDP新流填充不拖慢业务。028 schema/session接口是依赖，DNS直出与UI可先独立实现；030服务CLI可并行，main共享WAL/ABI单写入。

域名解析必须用原物理出口的bootstrap路径，DNS劫持/WFP与路由都要避开自身控制流，不能只在首次启动GetAddrInfo；保留业务DNS政策，不放行全机DNS。服务器地址≠借站SNI；Game一组固定endpoint，多A/地址变化不承诺跨独立server无缝迁移。

GUI只编辑“外层 MTU（字节，上限）”，**普通默认固定1460B、不含L2；1500B只能显式设为最大值，不能恢复为默认**；有效外层与自动内层/OS应用状态只读。保存/重连/切模式不能把内层读回写进外层配置，padding只用027A预算余量。

复用老网络/GUI/portable和现有flow/record padding，别换框架。padding默认off，flows模式有界、无等待、无每流线程，不因lane轮换或30s计时重复启动；实际MTU/首到优先。七模式换lane表归028，仅补域名/配置影响，不重新跑全性能矩阵。

自主计算和判断，先查真实调用链/旧成熟测试再修；不为假想极端堆防御，不用mock假装真实网络。代码/配置/帮助/UI/夹具同批齐，产物按SOURCE/hash复用；独立Actions并行，一Action一场景测量，同VM新旧顺序。容量止步、噪声不刷，保留真实失败。

每批短日志/功能卡/evidence，阶段更新cursor；可独立任务连续推进，按本包退出条件做完才交付。若整个028–030序列已授权再接后续，否则给030入口待验收，不无目标扩测。
