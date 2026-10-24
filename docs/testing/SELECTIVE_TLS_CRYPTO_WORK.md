# 独立选择性加密实验：永久入口

用户2026-10-24授权：新开分支，设计低系统开销架构和理想化成本/抓包测试，验证内层TLS正文不重复加密是否值得。当前只交付设计，**未开发实验数据面、未运行性能或抓包**。

工作分支 `experiment/selective-tls-crypto`。起点为FEC分支34985d2d，已含网络04074182。此岗位按用户直接授权独立推进，不领取M0–M4角色、不等待registry派单；不修改main、网络/FEC分支或它们的状态。任务范围限Normal单lane/FEC OFF与必要实验接线。

## 最小阅读

1. AGENTS/PROJECT_CHARTER与本页。
2. [架构](../architecture/SELECTIVE_TLS_CRYPTO_EXPERIMENT.md)。
3. [测试](SELECTIVE_TLS_CRYPTO_TEST_PLAN.md)与[机器可读矩阵](selective-crypto-matrix.json)。
4. [实时状态](../evidence/selective-crypto-work/status.json)及状态引用的最近日志/Actions。

不要执行继承的network/fec next_action，不全库加载历史；只在相关共享缺陷出现时回读源码和既有证据。后续上游修复按相关性冻结引入，不追浮动HEAD。

## 实施边界

- 先写一个独立实验record工具，使用真实aws-lc-rs和现有完整AEAD基准。已知TLS加密正文B作为AAD只认证、不再次加密；H/元数据继续加密。一次AEAD、逐包自含模式、无新密钥算法。
- 先理想oracle，不写通用DPI/重组/真实分类器。分类不确定就FULL，不等待，不基于443/包大小/熵猜密文。
- 生产默认/旧格式不动，Cargo实验feature默认关闭；新格式、MTU、HP10B、模式协商和安全边界要按架构完整实现，不能绕开认证做快分支。
- 采用S0→S1→有限S2→S3。资源测量和抓包分开；早做重复密文反例。外观失败可以结束实验，不能为了通过自动加入大段变换和复杂缓存。
- 一性能Action一场景；A/A-layout/B同job顺序。native ARM64优先，x86一个代表。构建一次复用hash，容量不足停止加压。
- 结果如实分为算法、记录、整机、外观；不能把理想分类器省略的开销藏成实际产品收益。

## 接班、写入和结束

每次刷新本分支，核未提交内容/父SHA/Actions。中断后补事实日志，状态旧字段归档，不覆盖失败/未测。实质变更同提交更新本岗位status+devlog；不要刷空确认提交。只做已授权完整实验，不自行合main/部署机器。

所有功能执行验证在Actions。本地允许只读审阅、编辑、差异/JSON/链接静态核对和数学计算，不把它们写为功能测试PASS。原始pcap有界、临时，摘要与hash保留，owned文件清理。

长期提示词见 [docs/prompts/selective-crypto.md](../prompts/selective-crypto.md)。它只导航实时状态，不复制过期SOURCE和派单状态。
