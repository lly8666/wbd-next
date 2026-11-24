# Android 临时 Root 实验分支统一与隔离策略路由入口（2026-11-16）

用户明确要求全部相关开发在 experiment/android-temp-root-probe。原实验从 1f8ef5ec 非强制 fast-forward 至 2e83f6b6，compare ahead4/behind0，迁回全部历史 capgate 代码、原 Action 43806012347 的 63/63 正反对照与 Action 43805552571 的真实 FAIL。新实验分支不再使用，main/M0 不动。

后续一律原分支：复用既有 android-root-probe-build.yml 的唯一 Bionic SOURCE/manifest/SHA256 构建，不在本 Action 重编。先 API28 与 API36 最多2模拟器再 API32；未成功不放行中间版本。

新增显式 routegate 模式。单次进程必须先确认 /proc/self/ns/net ID 可读，unshare(CLONE_NEWNET) 成功后 namespace ID 不同，而且新命名空间只有 lo。只有这些全部通过才允许操作：创建自有非持久TUN，配置 MTU1400/198.18.253.1/30，新命名空间路由表235仅一条目标198.18.254.2/32，fwmark 0x23500 优先级12000；无标记UDP必须不可达，标记UDP须被内核按规则送到该TUN并实际读取，关闭fd后接口消失。路由与规则只在新命名空间，进程退出即消失。CI检查Android系统规则/路由前后快照一致。若unshare/隔离失败，立即报告 ENV_BLOCKED，不写全局路由或使用替代方式。不会改 netd/iptables/NAT/转发/sysctl/boot/SELinux，也不会部署真机。

CAP_SYS_ADMIN 只是隔离夹具可能依赖的权限，不当成产品最低权限。即使通过，也不等于 Android netd fwmark、实际热点USB、App→su、转发或NAT产品功能通过。API37 SDK阻断保持原有结论。

本工作包结果 PENDING，等待真实且同SOURCE的 CI。无新的完整客户端/产品 PASS。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Fast-forward historical capgate proofs onto the original Android experimental branch and register a fail-closed private-netns fwmark packet fixture without touching Android global routes."}
```

## Feature catalog size correction

SOURCE a40fbc0b94512c4702a0724f81d3248a9a9683e3 hit governance FAIL: the feature-card JSON exceeded its 16 KiB byte limit. This docs-only correction retains every source-specific verification entry (including historical failures) but uses 1-space JSON indent and drops five obsolete/duplicated limitation prose entries. Their evidence remains in 20261116-final-report.md, 20261116-capgates-final.md, 20261116-api-matrix.json and 20261116-capgates-matrix.json. No Rust binary, test case or product claim changes.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Fit the complete source-specific verification card within 16KiB by compact layout and removing redundant prose; historical failures, PASS and NOT_RUN evidence remain in committed reports."}
```

## Routegate canary source-specific correction

SOURCE a40fbc0b94512c4702a0724f81d3248a9a9683e3: single native build Action 43808360398 SUCCESS, both API28 and API36 canaries Action 43808360345 reported **ENV_BLOCKED**; API32 skipped. Exact /proc/self/ns/net IDs did change (unshare succeeded). The preflight incorrectly checked /sys/class/net and found system eth0/radio0/wlan0, because Android's sysfs mount exposes the original mount-netns view; NO private TUN or rule was created and both global route/rule snapshots matched. Preserve this outcome; it is not a failed unshare or unsupported kernel policy routing conclusion.

This corrected SOURCE uses per-netns /proc/net/route to require an empty IPv4 FIB after exact distinct namespace verification, and uses namespace-aware RTNL link existence and SIOCGIFMTU ioctl instead of mounted sysfs for owned TUN cleanup/MTU. If namespace has existing routes, stop without writes. The only new route, mark, and packet are still strictly within the verified private namespace, never Android global routing. Build once and rerun only API28/36 canaries, API32 after success.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Preserve SOURCE a40fbc0 API28/36 ENV_BLOCKED due to mount-pinned sysfs preflight; correct private-netns inventory and cleanup via per-netns proc route and RTNL, no global route writes or product promotion."}
```

## Verified corrected SOURCE / final code and artifact evidence

Corrected `42cca27e8a6b8d4e5db38e72c2b3ddd0fef61b2d` compiled by Action43808870166, no rebuild per test. API28/API36 canary then API32/12L all independent Action43808870202 jobs **SUCCESS** and `SUPPORTED_IN_SCOPE`: distinct netns + empty /proc/net/route preflight, private table235/fwmark0x23500, 39B marked UDP on owned TUN, unmarked unreachable, MTU1400 ioctl readback and TUN cleanup; Android original route/rule snapshots identical. Exact IDs/SHA256 in 20261116-routegate-final.md / 20261116-routegate-matrix.json. Historical source `a40fbc0` ENV_BLOCKED unchanged. This is NOT system netd, NAT, hotspot, USB or App→su proof. All work on original experiment/android-temp-root-probe branch.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Register corrected SOURCE-locked API28/API32/API36 real isolated fwmark→owned TUN positive and negative kernel route evidence, retain first-source ENV_BLOCKED and Android netd/app-su/NAT/tether/physical NOT_RUN."}
```
