# Android临时root探测｜长期接续提示词

你负责 `lly8666/wbd-next` 的 `experiment/android-temp-root-probe` 独立实验。先恢复本分支实际HEAD和未提交内容，不去main接M0任务。只做临时root能力探针与Actions可行性验证，不直接开发完整Android客户端，不部署手机。

按顺序读：根AGENTS/章程 → `docs/plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md` → `docs/features/entries/android-temp-root-probe.json` → `docs/devlog/android-root-probe/` 最新日志及其Actions。先收已运行结果；上轮意外中断未留痕就据git/run/产物补事实再续做，不重复dispatch、不全读历史。2026-10-22旧方案暂停Android的限制已被本次“独立能力探测”授权覆盖，完整客户端仍未开工。

实施Rust轻量原生探针，必要时加薄Kotlin测试壳；默认只读，显式exercise才做owned临时改动。检查真正TUN读写、raw收发、权限/cap/SELinux、路由/fwmark、NAT/转发、DNS/IPv6、网络绑定/切换通知、后台与清理。无VpnService；不动现有FEC/重传/TLS/MTU核心；不安装root、不改system/boot、不关闭SELinux、不清空系统规则。热点/USB复用系统共享，offload和CLAT边界要查清；只有模拟转发不能宣布真实共享可用。

先在Actions测试Android9/API28到开工时最新稳定版（方案当前Android17/API37），包括12L/API32。编译一次按SOURCE/manifest/hash复用；最低/最新两个canary先跑，再补中间版本。一个Action一个模拟器/场景，独立Actions默认最多3条并行。确认KVM和镜像真实root能力，缺镜像/权限/性能受限如实分类，不循环重试或降低target/关闭SELinux刷绿。app→su、adb root、CI替身必须分开，root镜像不能证明真机root管理器兼容。

按计划短流量验证即可，不跑完整产品弱网/大吞吐矩阵，不拿AVD CPU声称手机省电。能独立判断的实现直接做，先完成一组连贯代码再验证；失败先判断代码、权限还是环境，再修受影响项，勿叠框架/钻牛角尖。测试代码、工作流、报告都以本任务前缀隔离；不改M0注册/游标、不取消别人的任务。

每个完整工作包留短devlog、精确SOURCE/Actions/hash和feature-impact；状态写回本功能卡，保留失败/未测。完成全版本结果表或明确受阻项、权限最小集、可行性结论和真机待验清单后收口。再次收到本提示词且任务已完成，仅报告完成与未验边界，不自行扩任务。
