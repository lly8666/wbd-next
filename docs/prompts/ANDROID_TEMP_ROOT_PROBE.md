# Android Root 原生客户端｜长期启动提示词（2026-11-17）

负责 `lly8666/wbd-next` **`experiment/android-temp-root-probe`** 上的正式 Android root 原生 WBD 客户端适配；用户已明确取消旧“只探针、不开发客户端”限制。仅此分支施工，最终 PR → main；main M0任务、registry/cursor不得直接改。每次先查远端最新HEAD/main、已提交变更、最近devlog/功能卡、在途Actions，聊天缺失按实际代码/证据恢复，不把历史SHA当最新；无远端worktree不能声称检查过未提交本地变更。

精简阅读入口：`AGENTS.md` / `PROJECT_CHARTER.md` → [现行施工方案](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md) → [产品功能卡](../features/entries/android-root-native-client.json) → `docs/devlog/android-root-probe/` 最新施工日志与Action；深历史按需查。旧探针历史在 [KSU 20261117](../devlog/android-root-probe/20261117-android-cn-geosite-dns6-kernel-final.md)，不继续增加合成按钮。2026-11-17已将main `0e57cab2d53e2c95962eb673050fa54695fd3665` merge到本分支，merge `d5126fcd4cc7c848b62181ebddf8dadcb4225397`；此时间点后的真实HEAD必须重新检查。

**主旨**：真实业务首到、p99/跨流无HOL、低CPU/低唤醒、有界内存和易维护。标准真实TLS ClientHello→认证/租约、Go冷控制+Rust成熟steady FEC/crypto/MTU/retransmission/generation/owned Stop必须复用；不能新Android协议/模仿TLS/按包Go/Java/JNI；直连用Android内核原TCP路径，WBD流才TUN；无VpnService/FakeIP。现有GNU/musl模块不得直接冒充Bionic可用；NDK ABI、arm64装载/16KiB、实际加速都要核。

**当前工作包**：A 产品装配→Normal/off Android KSU↔真实Linux WBD服务端。已固定原Go donor `a7a82db31fe736ffedee330795a3234d358f1984`，最新A1同SOURCE `c385502ab12a4e42c26e7a8beb57ec4aa68eb2f5` [Action44015392698] Android ARM64+x86_64 Bionic64+同一共享Rust冷owner导出+16KiB ELF BUILD_PASS（artifact14298207771）；原Go全产品链接 ARM64 FAIL 在Linux-only Rust M4 RAW/TUN/Health/MTU符号缺失，x86全链接NOT_RUN，真正TLS/server/PACKET绝不算通过。**唯一下一步A2：抽取已核验的共享M4驱动薄接口，真正连接Android ROOT TUN/Network-bound RAW至原Rust认证PN/AEAD/Stop，不能造stub或假产品成功**；之后A3用Android16 KSU到真实Linux服务端做标准TLS/认证/租约+双向TCP/UDP/Stop，同源证据仍NOT_RUN。B=主网络owned规则+无FakeIP统一双DNS UDP/TCP53+真实安装App选择/包名解析+手动规则更新，C=FEC/模式/回调切网/lifecycle/能耗，D=物理热点USB条件接入/PR。每包写齐有关代码/UI/配置/夹具后冻结SOURCE测试，不要每个函数刷大型Action。

**DNS**：仅全局普通DNS；CN域名开关（split默认开/global默认关），CN→223.5.5.5物理，其他→1.1.1.1隧道，关时统一隧道；server bootstrap一律物理；真实A后业务按IP/UID出网，非强制域名IP缓存；没有跨出口回退/每App DNS身份追踪/DoH劫持。每App跟随/分流/全隧道/直连，真实安装App列表与搜索/批量，不要求UID输入；内核CN共享集合，避免每App复制规则。全局IPv6不得禁，内层阻断按既有策略。按需离线规则+手动轻量更新，无周期唤醒。

**安全/运行**：已有root为前提，普通前台服务可出现；不提权、不刷机、不改boot/system、不关闭SELinux、不装常驻模块；原生root进程持有数据/物理socket，IPC低频。owned增量、compare-before-restore，不flush或篡改netd全fwmark、不让整个root UID绕路；App网络事件驱动同一成熟re-auth/MTU，不创建第二定时器。真机部署需明确设备授权。

**测试与停止**：所有自动测试用Actions，真实协议首次同源Linux server在Android16 KSU；一个Action一个网络场景，同 SOURCE/manifest/hash复用；未跑就NOT_RUN。先 Normal/off，后双DNS/2 App/模式/换网/Stop，10–20Mbps短验而非无止境优化；ARM64硬件、热点USB/CLAT/能耗真机需授权。每完整包更新功能卡/短devlog，记SOURCE、Actions、失败/未测和唯一下一步。main仅开工、真实连接后、最后整合前同步，历史不重写。完成授权范围、合理验收和PR准备即报告完成，不续造探针或优化任务。
