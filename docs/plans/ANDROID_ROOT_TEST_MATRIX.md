# Android Root 原生产品集中测试矩阵（B82 候选）

目的：一次构建、一套签名 ARM64 APK、一份可重复普通 App 流量夹具，先真实功能后性能；不做海量极端工况/重复x86探针。仅在用户明确授权的 ARM64 手机、受控 Linux 服务端及弱网环境执行。不因构建/Host或历史记录冒称新 SOURCE 真机 PASS。

## 1. 当前范围冻结

七模式（Normal/off、Normal Fixed、Normal Auto、Game2/off、Game2 Fixed、Game4/off、Game4 Fixed）、原Go TLS/认证/租约、原Rust M4、UDP/TCP、普通App单/组/all UID、内核直连、三DNS模式及系统普通53、真实Network、冷恢复/轮换、多配置、IPv4/IPv6软件热点、CLAT、SIT IPv6承载、startup padding、Game4 stagger、ARM64 ISA-L、outer v3、普通CN官方快照/手工导入/恢复、CN IPv4（B82含软件热点）均已源码接线或候选。旧MISSING台账行不再作当前依据。

非本次测试前置：连续热迁移/独立lane热轮换、业务idle-dormant唤醒、手机端一键联网更新CN数据（已有离线内置和用户文件导入）、Private DNS/DoH主动拦截、硬件热点offload/裸IPv6 M3；高级CN FakeIP明确OUT_OF_SCOPE，不实现。Windows专有驱动/服务端管理工具非Android客户端入口。不得把未实现能力标已接线。

## 2. 构建与环境

- 每个冻结SOURCE仅跑一次现有 Android dual64 CI。原Go/Rust双ABI、ARM64签名APK、两个原Linux Oracle、必要Host。保存同SOURCE/manifest/hash；不同场景复用同一APK和Linux产物，不重编译。
- 新 `traffic-fixture.apk` 为独立普通 UID，无Root、VPN或替代协议。CI Host只验证真实普通socket回显夹具与构建，不代表Android WBD。允许拿同一次产品CI产物在授权真机跑七模式。
- 最优环境：一台真实Root ARM64 Android + 同局域网/受控Linux服务器 + ADB控制电脑（用同一测试网络和服务端）。无需再采购资源或重跑SLIRP/TAP。GitHub hosted CI负责软件层，不用其模拟器冒充真机。
- 产品debug签名每SOURCE可能变，先冻结APK再跑所有场景；若以后需连续迭代，由用户授权使用本地持久测试签名密钥对候选APK重签；不把密钥上传仓库、不自动卸载/改签设备。首次签名切换先由用户备份配置、Stop并确认旧规则清除。

## 3. 真实App功能（顺序，单手机不并跑两个owner）

| 场景 | 实际最低证明 |
|---|---|
| Normal/off 基准 | SYN/SYNACK、原TLS/认证、/32、M4+UID Ready、普通App TCP/UDP逐字节双向、Stop |
| 其余六模式 | 同一测试UID与服务端，实际native mode/FEC/lane readback，短TCP/UDP双向，Stop；Auto换档另记观测 |
| DNS/直连/UID | 一个Normal代表场景覆盖单/组/all、绕过、普通CN和非CN两实际upstream、UDP/TCP53和系统resolver；不能以解析成功独立证明物理/隧道分流 |
| IPv6/热点 | 支持SIT的真实双方显式开启，测试IPv6实际地址、IPv4/IPv6下游普通应用；软件热点CN CIDR、普通DNS与Stop独立验证；CLAT视当前真实网络能力 |
| 生命周期 | 一次 Wi-Fi/蜂窝或以太网冷切换、一次配置切换、一次定时轮换，旧owner结束、新代真实Ready及业务恢复；非热迁移 |

所有失败保留实际阶段，不重刷已完成前置。与WBD连接无关的宿主/设备能力不足标 ENV_BLOCKED/NOT_RUN。

### 可直接重复的业务测试命令

在获授权Linux测试机的 **隧道内可达地址**（不是外层WBD peer IP，避免走server例外直连）运行：

```bash
python3 android/root-app/ci/traffic-fixture/server.py --bind <server-tunnel-ip> --port 18080
```

授权手机手工安装一次 `traffic-fixture.apk`。在 WBD Root App 选择 **WBD Traffic Test**（org.wbdnext.testtraffic）的普通UID，选择模式，等真实M4+UID Ready，再在ADB电脑运行：

```bash
python3 android/root-app/ci/traffic-fixture/run.py --host <server-tunnel-ip> --label normal-off --samples 32 --mib 4 --expect-uid <selected-uid> --output results/normal-off.json
```

其余模式仅改变 App 真实连接配置和 `--label/--output`，不用重装。可选 `--dns cn-name,non-cn-name` 测 Android 普通系统resolver；配合真实upstream计数判分流。IPv6可用真实隧道侧IPv6地址。原 `android/root-app/ci/device_first_run.py` 同时负责收集源、业务阶段和Stop路由记录；夹具 label不是原生mode证明，实际走M4需对照选定UID、M4真实增量与server收包。未授予设备/服务端授权时不部署。

## 4. 性能（正常功能之后）

用同一设备、网络、服务端、APK，避免同一手机并行场景争用CPU。先Normal/off代表，再Normal Fixed/Auto、Game2/4代表；对 outer off/on、ISA-L 实际 backend、padding off/flows 只做相关代表性 A/B。同一场景连续3次、顺序 A/B 与 B/A，固定数据量、MTU和背景负载。夹具记录TCP连接及首回包、TCP/UDP p50/p95/p99、成功样本、流式双向echo速率；正常短测4MiB/32样本，性能可增加样本/数据量。echo速率不是最大单向带宽；若要因果CPU或满带宽，另用真实单向stream/iperf3并对齐服务端字节、手机原Go/Rust进程CPU时间、墙钟和温度，记录空闲固定时间唤醒。只选一档代表性受控弱网（如10% loss），不在个人公网服务器随意设置netem。

## 5. 退出与交接

报告 SOURCE/PR/Actions、各真实阶段、场景PASS/FAIL/NOT_RUN/ENV_BLOCKED、延迟/交付/CPU/带宽。不改写历史证据。正常功能问题才修；不新设无业务价值的防御性测试门。不因某场景失败自动扩大功能范围。
