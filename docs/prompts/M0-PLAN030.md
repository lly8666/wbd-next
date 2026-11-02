# M0｜PLAN030接续提示词

你继续lly8666/wbd-next的PLAN030。先读START_HERE/AGENTS、M0长期提示词、最新registry/cursor、`docs/decisions/M0-LEGACY-ROLLOUT-20261102.md` 与 `M0-PLAN030-SERVER-CLI-DELIVERY-20261102.md`。默认上轮中断，先收在途结果/补增量留痕，不重复dispatch。仅用户实际启动才登记此包，不因文件存在抢占PLAN027。

目标：薄的wbd-next中文菜单/子命令，最小服务端配置（监听、借站域名、账号）、持久服务化、客户端快照与完整owned卸载。028负责账号/IP/每client配置，029负责Windows域名/DNS/UI；接口明确后菜单/包/unit可并行，真实验收不得使用假会话替身。

MTU设置指外层完整IP上限；server自动结合本地限制与client意图派生内层，不要求新增必填MTU/内层输入。clients快照分列外层设置、有效外层、自动内层，读027A结果，不在CLI重复计算。

优先搬旧wbdctl/service/config的成熟逻辑，去掉在线升级/回滚中心，不新增Web管理/监控daemon，不为CLI重写Rust数据面。clients默认一次快照，watch才2s读现有统计；没有质量样本就未知，不额外发探针。先Stop/网络恢复再删文件，不能先删WAL或清整机防火墙。

一批写齐CLI/config/help/unit/打包/功能卡再测，Actions产物按SOURCE/manifest/hash复用；功能可顺序合批，性能一Action一场景，其他独立Action并行。真实systemd安装→多client→启停→配置→卸载重装；域名重连组合只补影响，复用028七模式换lane，不重复大矩阵。arm64构建与原生运行、服务restart与机器重启分别留资格。

大胆做普通实现决策，站在实际可用、低开销目标选择最短路径；发现不合理要求提出依据修订，不机械刷门或扩防御框架。短日志/功能卡/证据/cursor接续，保存失败/NOT_RUN。必要功能与受影响验证齐就交付，整序列已授权且完成则明确待验收，重复提示不再扩测。
