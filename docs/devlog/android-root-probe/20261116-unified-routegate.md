# Android 临时 Root 实验分支统一与隔离策略路由入口（2026-11-16）

用户明确要求全部相关开发在 experiment/android-temp-root-probe。原实验从 1f8ef5ec 非强制 fast-forward 至 2e83f6b6，compare ahead4/behind0，迁回全部历史 capgate 代码、原 Action 43806012347 的 63/63 正反对照与 Action 43805552571 的真实 FAIL。新实验分支不再使用，main/M0 不动。

后续一律原分支：复用既有 android-root-probe-build.yml 的唯一 Bionic SOURCE/manifest/SHA256 构建，不在本 Action 重编。先 API28 与 API36 最多2模拟器再 API32；未成功不放行中间版本。

新增显式 routegate 模式。单次进程必须先确认 /proc/self/ns/net ID 可读，unshare(CLONE_NEWNET) 成功后 namespace ID 不同，而且新命名空间只有 lo。只有这些全部通过才允许操作：创建自有非持久TUN，配置 MTU1400/198.18.253.1/30，新命名空间路由表235仅一条目标198.18.254.2/32，fwmark 0x23500 优先级12000；无标记UDP必须不可达，标记UDP须被内核按规则送到该TUN并实际读取，关闭fd后接口消失。路由与规则只在新命名空间，进程退出即消失。CI检查Android系统规则/路由前后快照一致。若unshare/隔离失败，立即报告 ENV_BLOCKED，不写全局路由或使用替代方式。不会改 netd/iptables/NAT/转发/sysctl/boot/SELinux，也不会部署真机。

CAP_SYS_ADMIN 只是隔离夹具可能依赖的权限，不当成产品最低权限。即使通过，也不等于 Android netd fwmark、实际热点USB、App→su、转发或NAT产品功能通过。API37 SDK阻断保持原有结论。

本工作包结果 PENDING，等待真实且同SOURCE的 CI。无新的完整客户端/产品 PASS。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Fast-forward historical capgate proofs onto the original Android experimental branch and register a fail-closed private-netns fwmark packet fixture without touching Android global routes."}
```
