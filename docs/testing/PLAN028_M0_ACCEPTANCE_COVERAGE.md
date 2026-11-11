# PLAN028｜M0 当前功能、正式入口与集成覆盖（2026-11-11）

**状态：IN_PROGRESS，不是收口证明。**此页是接续导航，规范门槛仍以 [PLAN028_INTEGRATION_ACCEPTANCE](PLAN028_INTEGRATION_ACCEPTANCE.md) 为准。功能卡见 [inventory](../features/inventory.json)。旧证据不被新源码重新标记为 PASS；失败 Action 原样保留。历史矩阵仅按所列 SOURCE/平台/场景有效。不得开展 PLAN029 DNS/填充新能力或 PLAN030 服务管理。

## 当前入口、产物与证据规则

- **Linux x86_64 / ARM64：**原始 Go credential TLS443 冷协商、`r0/go_overlay/internal/v4productcli/linux.go` 的当前 CLI、`crates/wbd-engine` Rust M4 和原生 raw/TUN。Windows/Linux 开发源码在 `main`、原始 Go 固定 donor `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`；`r0/go_overlay/assembly/manifest-plan020-m0.json` 固定每一正式替换/新增 Go blob。ARM64 **不**能只凭仓库存在文件：要核正式 H1546 11 文件装配 + 实际后端与 binary receipt。
- **Windows x86_64：**正式 `wbd-client.exe` 默认 `--native-v4-product=true`；WinForms `windows/gui/Portable.cs` 经当前 manifest 组装后显式启动同一 `--native-v4-product --control-stdin --config` 子进程。默认 false 的旧隐含入口已取消，显式关闭不会自动退回旧 V3。正规装配为 `tools/prepare_windows_wiring.py` + `r0/go_overlay/assembly/assemble.py` + manifest；`EXTRA_BRIDGES` 明列 Game group 和原生认证附加桥。Go只负责认证/冷路径，Rust为收发/记录/FEC稳态；签名 Npcap/Wintun/OS WAL 为真实产品硬门。
- **最新实际测试源码：**`fd4732ec4adffa442a0bc25a145ed6ea1d1259a8`（H1592实网/二进制），`813e4c5c71fe2a1f2442bfda0ce19c205a398d03` 为最初Windows自动IP/三cipher接线源码、不是最新HEAD。`fd4732ec` Action `43009320538` 实Windows30%冷TLS+M4+签名OS+Stop成功（**仅冷建链**），`43009320436` Linux x86/ARM手动两账号真实TUN/Stop成功，`43009320389` Windows各模式/WAL scoped通过；旧SOURCE `dd82db7e` Action `43000134310` 真实Windows自动AES256+四Linux三cipher150s严格报告PASS_SCOPED（Action整体后置FAIL）。**Windows单宿主双独立Wintun路由H1587仍FAIL；SOURCE `8c0421c3` Action `43014043726` Windows自动AES256/四Linux三AEAD真150s/六owner Stop已PASS_SCOPED，不能写全组合均通过。**
- **二进制/装配指纹：**H1376 同源码 x86_64 artifact ZIP `sha256:fb36ebb74b02251afd152dc83e0945d3ff40ba83c2ec7f88e8cc4e11598ca5a9`；ARM64 `sha256:1aa746cc6b6a8d44d52437ce3cf9ea1e95a63f6f9c693074138766b98b2c108c`。H1546 ARM64 构建收据 artifact ZIP `sha256:38afc2fdd7c645e90e49305c802f90c480de3df5a89bc817c90d1c3444ea98a1`。这些是**artifact ZIP digest，不可冒充 exe/dll/rust .so 的单文件 SHA256**；逐文件 hash 与后端以 artifact 内 receipt 为准，未核的单文件字段标 NOT_READ。
- **不混淆容量/范围：**H1577 `cd5dfa3b7688167eebfc12020e0180a9fa8df8f4` Action `42983815178` 曾真实完成 Windows+4 Linux 150s 1.15× 六角色 UDP/TCP、Windows先退出后 Linux继续、六个 native Stop/WAL/WSL/netem 清理（`PASS_SCOPED`）；Action 整体 **FAIL** 是后续复制缺失 `normal-report.json`。新脚本仅在真实完整场景成功且所有资源恢复后导出带 `TRUE_150S_FIVE_CLIENTS_NOT_600S` 的兼容报告。原始失败必须保留；**未跑 600s，不等于新 SOURCE 813 的网络 PASS**。另有较早外层约 304 Mbps **双向总量**弱网证据，不能解释成单客户端内层 304 Mbps。
- `42984484136` 治理 12 FAIL、`42987330788` 3 FAIL 均保留；更正旧断言后的 `42987762293` 治理回归 **PASS**。旧 `42987762872` Windows WAL 因 PLAN022 过期仅Normal/off 文本门而 FAIL（原 Go native 构建与测试实际通过），修复后的 SOURCE 回归仍应核对。

## 配置核对表（默认≠自动开启）

| 功能 | 当前默认 | 正式入口及实际传递点 | effective/OS 读回 | 支持与当前资格 |
|---|---|---|---|---|
| 传输模式 / lanes | Normal 1；Game2/4需显式 | Linux `--mode normal/game2/game4`；Windows `lanes=1/2/4` / GUI传输→原Go `m0ParseWindowsV4Mode`→受保护TLS→Rust owner | `DesiredLanes`、Rust group lanes、ready/owned Stop、物理包与server按lane验 | x86/ARM/Linux原生资格有 SOURCE813 代表；Win 7 模式原生旧SOURCE `b6b964...` / `33ed20...`，新源各组合 NOT_RUN |
| FEC Off / 固定 / Auto | **Off**，不是全部开启 | Linux/Windows `fec-mode` 默认 `legacy` 且 `fec-parity=0`，显式固定最高R20、Normal Auto；Game2/4固定最高；GUI已有 `fec.mode` 旧新选择映射需辨别 | 原 TLS FEC policy→Rust actual FEC parity/profile 和真实mode，not GUI save | 七覆盖模式：Normal Off/Fixed max/Auto，Game2 Off/max，Game4 Off/max；旧源码证据可复用未变组件，Windows新入口组合需补 |
| record cipher | **ChaCha20-Poly1305** | CLI / JSON / GUI `record-cipher=chacha20-poly1305|aes-128-gcm|aes-256-gcm`；`main_windows.go` patch→`RecordCipher:suite`→`PolicyForClientWithInitialAndCipher`→原始TLS | Windows Normal `session.ColdSnapshot().Cipher()`、Game每lane `group.AuthenticatedNetworkSelection()` 与请求值一致；拒绝未知组合 | H1586老源Windows AES256+Linux三AEAD真业务150s PASS_SCOPED；H1587 A AES128真OS业务通过、B ChaCha第二Windows OS **FAIL**；H1592 Windows ChaCha冷建链PASS、GUI人机未验 |
| 自动 / 手动 IPv4 | 客户端 `lease4` 留空=自动；显式 `a.b.c.d/32`=手动 | Windows 原Go CLI/JSON `autoLease`→每组受保护 `ClientAdmissionConfig.AutoLease`，Linux复用成熟服务端lease池/手动映射 | `AuthenticatedLeaseIPv4()` 获取受保护真实 /32→ `o.Lease4`→Wintun NetworkPlan/OS WAL；手动验证租约匹配；Linux OS readback | `dd82` Windows真正自动/32 OS+AES256 150s通过；`fd473` 手动Windows/32 OS读回、Linux x86+ARM双手动真OS与Stop通过；单宿主双Windows手动OS H1587失败，同账号跨终端新源额外组合未验 |
| 用户外层 MTU | **1460 B** 完整IPv4 IP（不含L2）；1500只显式 | Linux `--outer-mtu`，Windows `--mtu`/JSON/GUI当前默认1460；Rust `path_budget` 针对实际封装/FEC/peer限制作唯一冷预算 | Rust实际outer/inner/MSS，Linux TUN及Windows Wintun `RuntimeMTU` OS读回；不得拿1500/9000旧示例当默认 | 已有旧SOURCE正常/1280/近边界分场证据；SOURCE813新auto/AES边界 NOT_RUN |
| 外层机会式重传 | **on**；不承诺业务可靠性 | 双端 `outer-repair on|off` 原生Go→Rust bounded ciphertext shadow | Rust generation/ciphertext固定、实际 repair candidates/发送，保持健康与FEC独立 | 老源码真实差异及压力有有界证据；不恢复TCP全重传、不伪称损包必达 |
| lane 轮换 | **Linux interval=0**；Windows `rotate-min/max=0/0` | 显式成对区间/真实已有 lifecycle controller 和 Health | A→A+B→B 切换、失败保留A、Game兄弟业务持续、old generation Stop/资源CAS | SOURCE813 x86 Game4 overlap Action `42987762898` PASS；Windows auto/cipher新配置回归未齐 |
| keepalive 与 dead | **Windows 15s / 90s** | `keepalive-interval` / `dead-after` JSON/CLI→原Rust Health/Go重认证；服务端按自身配置 | Rust实际 authenticated health/dead、原生 reconnect 和 owner Stop；不能把TCP ACK当Health | 历史Linux失联真实105s/106s黑洞复原可复用未改组件；SOURCE813 Windows认证修改后的代表场景 NOT_RUN |
| idle / 业务唤醒 | **Windows idle-dormant=0**（不自动休眠） | 显式 `idle-dormant`，真业务刷新payload idle，Health不可刷新 | 双边auth idle→Dormant；真业务 WakeDemand→新TLS/Rust，显式Stop不复活 | 历史Linux100s零业务后新UDP PASS；Windows新源真实idle/Wake NOT_RUN |
| 原生路径变更 | 仅真实物理出口/源IPv4/有效MTU变化触发（不默认频繁轮换） | 原生 Linux netlink/Windows NotifyIpInterfaceChange→200ms静默/500ms上限去抖→新代原TLS/Rust和OS计划 | 冷OS三项实际读回、new owner ready后old generation CAS Stop；同NIC实MTU降低亦处理 | x86 Game4新源代表PASS，Windows真实NPF/OS path及同addr-MTU缩小旧源 scoped；新源auto未验证 |
| DNS/分流/IPv6兼容 | 保持既定当前产品默认，不新增029能力 | Windows已有 `dns4`, `direct4`, `route-mode`、IPv6拦截；Linux路由沿现有CLI | owned OS/WAL DNS route readback 与退出恢复；当前测试只做兼容冒烟 | SOURCE813新认证/租约受影响路径须短测；029新增域名/DNS策略和030服务管理 **范围外** |

所有表中“default”与运行“effective”分别由 `--check-config` 配置值、原TLS协商、Rust snapshot、原生 OS WAL/MTU 和真实数据收发读回支撑。**`--check-config` 或 GUI保存≠成功安装 OS/业务首发**。当前没有一份新源码覆盖所有路径且含字节/后台 backend/p99/队列/CPU/RSS 的综合报告。

## 028 收口覆盖表（保留 hard gate）

| 功能/场景 | 平台 | 正式入口/默认 | 精确 SOURCE / Actions / 证据 | 当前结果与限制 |
|---|---|---|---|---|
| 标准TLS443/无私有前置消息/账户绑定 | Linux x86_64 / ARM64 Go TLS+Rust | 原生服务端/客户端；单端口 | `813e4c5c...` Actions `42987762909`,`42987762119`,`42987762125` | 单场真实原TLS和两账号手动独立 `PASS_SCOPED`；不等于Windows全部cipher |
| 多账号手动/32、A退出B续收及 Stop | Linux x86_64 + ARM64 | server共享Rust TUN，客户端手动 | `813e4c5c...` Action `42987762119` 双平台 | `PASS_SCOPED`，真实 native Go TLS/Rust、账户手动地址隔离 |
| Game4 A→A+B→B / 中途MTU | Linux x86_64 | Game4显式，FEC profile按场景 | `813e4c5c...` Action `42987762898` | `PASS_SCOPED` 共享单TUN、真实TLS、切换/Readback；不是Win新Auto |
| Windows Npcap/Wintun normal+四Linux 150s 1.15x | Win2025 + Linux WSL2 | Native V4，原测试显式1.15× | `cd5dfa3b7688167eebfc12020e0180a9fa8df8f4`, Action `42983815178`；新`8c0421c3` Action`43014043726` 真实1.0×150s | 旧1.15× UDP/TCP/六owner scoped PASS但Action后置FAIL；**新 SOURCE** 1.0×150s五客户端UDP/TCP/Alice先Stop Bob继续/全Stop **Action SUCCESS、业务PASS_SCOPED**，不是旧1.15×压力重跑 |
| Windows自动/手动IP、三AEAD不同终端同服 | Win2025 signed driver ↔ Linux shared | V4默认；`lease4`空/32、`record-cipher`默认ChaCha | 新`8c0421c3` Action`43014043726` [H1594证据](../evidence/M0/PLAN028-H1594-SOURCE8C042-WIN-AUTO-AES-LINUX-FOUR-REAL-150S-PASS-SCOPED-20261111.json)；另`fd4732ec`30%手动冷场；`3b6d53c3`双Win路由失败 | **Win自动AES256+Linux三AEAD真实150s+全Stop PASS_SCOPED**；fd473 Win手动ChaCha30%冷TLS/OS PASS_SCOPED；同主机第二Windows路由冲突FAIL，同账号两独立设备全部OS场未验 |
| 七模式产品正向 | Windows/Linux x86_64 + ARM64 | Normal Off/max/Auto、Game2 Off/max、Game4 Off/max，FEC默认Off | 旧 `b6b964afa7ffec5795f2c11c6e0620f223e684ac` Action40560287417、旧 `33ed20...`；新的Win编译813 | 老源七模式真实正向可复用非改动组件；Win新源模式/cipher搭配 NOT_RUN |
| Windows可用B前不得退休A、Game兄弟不断 | Win2025 | Native有界轮换 | Windows历史source与813 source-mode tests；`42987762319`双独立原生owner槽 | SOURCE813 Windows owner/生命周期 unit PASS，整机Path/Auto runtime未验 |
| keepalive/idle/dead与真正payload唤醒 | Linux x86_64 | 15/90 Windows，Linux实配；默认idle0 | 老 `134914f4263f905047b1096c771609558bcdde82` 真黑洞/新TLS恢复；原计划原证据 | 历史 Linux `PASS_SCOPED`；Win新SOURCE组合代表 NOT_RUN |
| ARM64持久、30%丢包/轮换 | Linux ARM64 双端 | Native Rust, Go TLS | `24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73` H1361/H1363及历史长测 | 老源码受未改组件可复用，SOURCE813 arm64正向手动租约PASS、ISA-L构建PASS；不冒充new 1800s |
| Windows 30%物理损伤单个冷TLS | Win2025/WSL2 | Native首次ColdTLS，不要求全负载 | `fd4732ec` Action`43009320538` + [H1592 evidence](../evidence/M0/PLAN028-H1592-SOURCEFD473-WIN30-COLD-TLS-PASS-SCOPED-20261111.json) | **PASS_SCOPED冷建链**：原Go RTO3次、TLS/Rust、签名Wintun实际/32 MTU1389、Linux真反向源、双方owned Stop；30%五客户端150/600s与L3 **NOT_RUN**，旧source失败不改写 |
| Linux/Windows数据、CPU/RSS、p99、PPS、连续空洞、队列年龄 | x86_64/ARM64/Win | 压力只到平台能力、同 VM A/B | H1577 `cd5d` 150s、ARM64旧30m证据、旧外层304Mbps双向总量 | 现源码代表容量及一套新配置全链指标未齐；不能以成功包p99代替未交付 |
| 完整单端Stop、原始网络恢复、共享server退出 | Win+Linux | 客户端仅回收自有网卡/路由/WAL | `8c0421c3` H1594 Action`43014043726`；旧H1576 `c3e6`, H1577 `cd5d`失败记录 | **新源真实五客户端150s Windows精确退出→Bob再收4 UDP→Linux四端和共享server Stop/WAL/netem/WSL恢复 PASS_SCOPED**；旧Action FAIL保留；双Windows同宿主 Stop隔离 H1587仍FAIL |
| DNS、分流、IPv6、近MTU小/大包兼容冒烟 | Win/Linux | 沿已有默认，不开发029 | 历史兼容烟测 + Rust budget code | SOURCE813新auto组合未完整验证 |
| Android、物理公网、029新增DNS/填充、030服务 | Android/物理/未来 | 不接入本轮 | 无本SOURCE资格 | **范围外/NOT_RUN，不能作为已验** |

## 优先收口顺序（防止重刷同类）

1. 收完新 SOURCE Actions 的实际结果、提取产物文件 SHA256/后端和 OS readback；工作流自身文本门过期要修，但不能降低原生业务门槛。日志和旧失败保持可追。
2. 在真实 Win2025 Npcap+Wintun、原始Linux共享服务端上先做自动IP、手动IP、ChaCha/AES128/AES256互异客户端同账号独立安装ID，强制同时验证TLS受保护返回IP、Rust cipher、真实OS /32/MTU和 UDP/TCP；未知组合拒绝。首选真实短场，再有必要才 L2 负载。
3. 针对改动生命周期做代表 A→A+B→B、候选失败保留A、idle/keepalive/唤醒与一客户端退出其他继续；按原 L2 渐进压力和能力实测。对受影响的 Win 30% cold TLS 在网络容量和认证门允许后再做业务。
4. 冻结通过的新源码，复用旧 ARM64未改组件的30m结果，**只给认证/租约/Windows新路径补代表综合真实场景**。写完整源和每binary hash/backend、功能卡与devlog/状态；所有阻断关闭前不得把 PLAN028 改 Completed。

**本页不改变任何硬门或既定产品默认。**历史失败记录应保留并按产品/夹具/宿主进行诊断，不把局部业务 PASS 写成整场 PASS。


## H1582 构建产物校核补遗（不越界宣称）

原始 Action 内 `fixed-build/manifest.json` 和 `arm64-public-bundle/{manifest.json,SHA256SUMS}` 经下载读取，逐文件 **SHA256是CI生成的实际build-output hash**，ZIP只带收据而未带原始二进制，故本地无法独立重算二进制本体。完整原始凭据留 [SOURCE813 per-binary evidence](../evidence/M0/PLAN028-H1580-SOURCE813-PRODUCT-BINARY-SHA256-20261111.json)。

| 精确 SOURCE / 平台 / Action | Go client SHA256 | Go server SHA256 | Rust库 SHA256 | backend/限制 |
|---|---|---|---|---|
| `813e4c5c` Linux x86_64 `42987762119` | `7f347ae9dc878edf508aa5fdeb8668ccae653682d01898435b69d42c94a555d1` | `9188f3941eba3dfd48831f779e0d8b73d3b31deda4c1978a1f270e11d75dcc71` | `4516b999a4b7cc2882439383faf5e73e711cc4b1a6197257b3751e192bc2e679` | Go1.23.12 TLS+Rust1.85.1 M4；两账号原生TUN业务/Stop已按H1376范围PASS |
| `813e4c5c` Linux ARM64 H1376 `42987762119` | `4d59a0fe3e7bf7a651b120c577938878683600d62b043e4e3f43fbfaaeb0f38f` | `a347a445174233e25a2d895ba3add181d72cb01b3b9c40d9a4ff83912b9c0890` | `8e10f70a819e2d9f3f9aa45588ddcc91976b243d851c32d3bc63c663ea7c56e1` | 基线 Rust 1.85.1 原生TUN业务/Stop H1376 PASS；不等同ISA-L版本 |
| `813e4c5c` Linux ARM64 H1546 `42987762189` | `4d59a0fe3e7bf7a651b120c577938878683600d62b043e4e3f43fbfaaeb0f38f` | `a347a445174233e25a2d895ba3add181d72cb01b3b9c40d9a4ff83912b9c0890` | `ed53bfa10502fb3015b69150bf45e87926924a5d05b2985c0dcd48aa9bf71547` | ISA-L aarch64 static链接、11源Go overlay完成，**运行时NEON分派未验**，此套只BUILD_PASS |
| `813e4c5c` Windows x86_64 `42987762859` | `NOT_READ` | 不适用此client编译Job | `NOT_READ` | Windows-Go/Rust **compile PASS**，artifact未附可独立验证的exe/DLL SHA，待新H1582 signed-OS strict report |

`assembly.json.actual_product_engine="NOT_WIRED"` 是通用 assembler 收据自己的阶段，不是H1376之后原始Go/Rust/TUN运行时后端判定；不能反向当全平台 product NOT_WIRED，也不能把H1546的静态ISA-L链入误当NEON实跑。H1581 SOURCE `ca9b744e` Action `42992510288` 首次仅成功编译，管理路由fail-closed后产品未跑；H1582 `3f82fad8` 的真业务、当前exe/DLL SHA仍应读它自己的原始报表，SOURCE813数字不得移植为新源码二进制。


## H1589 真正 Windows2025 后续重验（以原始 SOURCE 和作用范围区分）

| SOURCE / Action | 真产品证据（不是编译） | 严格范围及未过门 |
|---|---|---|
| `dd82db7e` H1586 `43000134310` | **原始strict-native-report PASS_SCOPED**：Alice Windows自动 `10.66.0.207/32` + AES256/Rust3 + 签名Wintun OS；Bob/Carol/Dave/Erin四Linux各独立/32及ChaCha/AES128/AES256，五真正kernel UDP/TCP双向150s；Alice Stop后Bob仍UDP、六owner Stop、Linux Rust TUN `reader_joined=1`；见 `docs/evidence/M0/PLAN028-H1586-SOURCEDD82-WIN-AUTO-AES150-NATIVE-PASS-SCOPED-20261111.json` | **Action overall FAIL**：仅旧Normal专用两OS后置报告误套；H1589限定后置分支修正。真正600s、250–300Mbps双向外层、loss30、L3仍NOT_RUN，不能宣称全PLAN通过 |
| `3b6d53c3` H1587 `43001721886` | A Windows手动AES128 TLS+Rust+OS Ready+双向业务；B Windows手动ChaCha TLS+Rust、Linux共享server分别见cipher2、cipher1 | **FAIL**：B route/WAL `route is not owned; refuse to replace`，B独立OS /32/双业务、A Stop B继续、双WAL安全Stop未通过；需修原生 OS route owner设计，不能松guard |
| `5f0ac32b` H1588 `43002178705` | 真30%双向netem/200ms单程，Npcap原始TCP SYN/SYNACK、MSS1420，原Linux server TLS443和真Linux UDP sender已启动 | **FAIL**：15s FakeTCP bootstrap deadline；证书TLS未过、Rust M4/Windows OS/反向包NOT_RUN，不能混入之前H1583曾完成TLS而未完成反向的不同SOURCE |

所含逐文件Windows Go/Rust、Linux Go/Rust和签名Wintun SHA256按 **每次Action原始artifact** 使用；同一次CODE里旧Windows Go hash偶然相同不授权跨SOURCE产品证明。新H1589源级修订不会重写 dd82 Action overall；所有其他功能卡/工况仍等待正确范围内真实回归。


## H1592 接手真实结果与修正测试资格（SOURCE锁）

- **冷 TLS 30% 正向**：`fd4732ec4adffa442a0bc25a145ed6ea1d1259a8`，Action [43009320538](https://github.com/lly8666/wbd-next/actions/runs/43009320538) 整体 **SUCCESS**，原生 Win2025/WSL2 job `130487172012` strict-native `PASS_SCOPED_H1579_WIN30_COLD_TLS_M4_OWNED_STOP`。有真实双向 netem 丢包30%、单程200ms、原Go冷TLS重传 **copied=3 / joined_before_Rust_M3=1**、证书/凭据受保护TLS、Rust M4双方、Linux真实kernel反向UDP、签名Npcap+Wintun手动 `10.66.0.2/32`、有效内层MTU **1389 OS读回**、Windows 15s/90s/idle0 readback、server `reader_joined=1` 与 Wintun/WAL/netem/WSL Stop清理。原始artifact ZIP SHA256 `79f241b2537e2e78e8b41791ccc28b43dfd9637394cd45e48d8da62d6c89fee8`；逐构件 hash 见 [H1592 evidence](../evidence/M0/PLAN028-H1592-SOURCEFD473-WIN30-COLD-TLS-PASS-SCOPED-20261111.json)。**未运行**30%五客户端150s业务、600s容量及1800s综合长测，不以冷建链通过代表它们。
- 同 SOURCE 的治理与feature目录 Action `43009320451` 整体SUCCESS；原Go Windows WAL/Normal/Auto/Game2/Game4/Fixed scoped Action `43009320389` SUCCESS；Linux x86/ARM两账号手动地址原生 Action `43009320436` SUCCESS。先前 `42979705842`、`42979705889`、`43008382596`、`43008382493` FAIL 原始记录不变。
- **发现真实报告缺陷并修复**：上述成功的原 `normal-report.json` 将短冷建链的 `qualification_scope` 错写为 `ORIGINAL_600S`，尽管严格原报告显示 `600s_outer_capacity=NOT_RUN_H1579_SHORT_30PCT_COLD_TLS`。H1592将字段改为 `COLD_TLS_M4_STOP_ONLY_NOT_600S`，收紧既有后置scope检查并补源级测试；不更改真实场景、硬门或产品，不拿报表修复充当网络再验。
- **仍阻断收口**：H1587 SOURCE `3b6d53c30531f6820c220f9e6c23f8a23480227c` Action `43001721886` 双Windows真实签名/同宿主共享路由第二实例 WAL `route is not owned; refuse to replace`，B的独立OS /32/双向业务及A Stop后B存活未证；禁止删除不属于B的捕获路由或弱化CAS。当前Windows本宿主两套默认 `/1` 捕获与server `/32` escape路由需要明确安全共享/路由策略，单纯 TLS+Rust 鉴权无法证明OS同时隔离。
- **下一代表业务**：新源码文档/报告修订后仅对变更过Windows冷建链的自动AES256+四Linux三cipher 150s实网安排一场独立 `[plan028-h1581-win-auto-aes-mixed-150s]`，完成后再更新精确SOURCE/Action（无真报告时标NOT_RUN）。L2容量/断流/CPU RSS及最终L3、双Windows并行仍须按专项硬门取证，PLAN028仍 **IN_PROGRESS**。


## H1593 新同源正式产物实体哈希复核（不是冒充三平台都重新实网）

取回 H1592 `fd4732ec4adffa442a0bc25a145ed6ea1d1259a8` 的 Actions 下载 artifact，Windows x86 和 Linux x86 构件 **ZIP中含实体**，本地解压逐文件再次计算 SHA256 与 CI manifest 全部一致。Linux x86 实际 `wbd-v4-client --help`（该正式二进制，`LD_LIBRARY_PATH` 指向同包so）确认 Normal、`--outer-mtu` 默认1460、`--record-cipher` 默认ChaCha、`--outer-repair` 默认on、`--game-fec` 默认off、`--rotation-interval` 缺省0；`--fec-profile` 数值默认1仅为显式固定模式的参数，并**不**表示开了FEC。真实Windows标记显示 keepalive15/dead90/idle0、OS inner1389及上述认证有效值。

| 平台 / 来源 | 正式 Go client SHA256 | 正式 Go server SHA256 | Rust运行库 SHA256 | 校验后端 / 范围 |
|---|---|---|---|---|
| Win x86_64 SOURCEfd473 Action43009320538 build artifact`13850805988` | `63b4a24abb0e7c775be5e58d3e54036f4bfab0491bc992a0147b8fe57886cd7c`（Windows exe） | Linux共服另列 | `f68c286f23c92ca3b45ec76eb484265e8559c576a3af493cadd0fa34a6957048`（Windows dll） | **本地按实体重算MATCH**；原Go认证+原Rust M4、ISA-L静态链接；另signed Wintun hash `e5da8447dc2c320edc0fc52fa01885c103de8c118481f683643cacc3220dafce` CI报告，本包不含Wintun字节 |
| Linux x86_64 同源 artifact`13849279449` | `7f347ae9dc878edf508aa5fdeb8668ccae653682d01898435b69d42c94a555d1` | `9188f3941eba3dfd48831f779e0d8b73d3b31deda4c1978a1f270e11d75dcc71` | `2947d148d325e198acd920c56803ad168175ba11590396478682693fcf5922dc` | **三个实体本地重算MATCH**；Rust native_fec_acceleration=true，Linux真实手动双账号TUN另有43009320436 |
| Linux ARM64 native 同源 artifact`13850260737` | `4d59a0fe3e7bf7a651b120c577938878683600d62b043e4e3f43fbfaaeb0f38f` | `a347a445174233e25a2d895ba3add181d72cb01b3b9c40d9a4ff83912b9c0890` | `8e10f70a819e2d9f3f9aa45588ddcc91976b243d851c32d3bc63c663ea7c56e1` | **仅CI生成manifest、无实体本地重算**；源锁真实原Go TLS两账号手动/32、59 UDP、reader Stop PASS_SCOPED |
| Linux ARM64 ISA-L 同源 artifact`13850715104` | `4d59a0fe3e7bf7a651b120c577938878683600d62b043e4e3f43fbfaaeb0f38f` | `a347a445174233e25a2d895ba3add181d72cb01b3b9c40d9a4ff83912b9c0890` | `ed53bfa10502fb3015b69150bf45e87926924a5d05b2985c0dcd48aa9bf71547` | **仅CI SHA256SUMS、编译/11源overlay/加速链接PASS**；此加速版原生TUN及NEON运行时 **NOT_RUN** |

以上 checksum 均是具体二进制 SHA256，**不是ZIP的hash**；ZIP SHA见H1592 evidence。不同 Rust库hash分别对应普通原生与加速构建，不混用、不得将BUILD_ONLY写成ISA-L业务真测。Windows本源15s/90s参数/MTU readback、真实签名驱动入链的场景以H1592原始Strict报告为准。



## H1594 最新原始 Windows2025 五客户端150s 实测（SOURCE8c0421c）

Action [43014043726](https://github.com/lly8666/wbd-next/actions/runs/43014043726) 和native Job`130502884187`均 **SUCCESS**；从artifact`13852862215` 原始strict report/原始Windows/Linux日志复核，ZIP SHA256 `75db8322f08830f2d5c11a300ab4f7a10bff731862bc68f5fcffcb366164562d`；严格报告SHA256 `f3229ac51e5b33d4e36097343e63ad70d65b1920ac3191c6f2bc719286098f3b`，详细[H1594 evidence](../evidence/M0/PLAN028-H1594-SOURCE8C042-WIN-AUTO-AES-LINUX-FOUR-REAL-150S-PASS-SCOPED-20261111.json)。

| 轴 | 新源真实入口/有效值 | 收口范围 |
|---|---|---|
| Windows原Go TLS+Rust+OS | Alice auto真正受保护`10.66.0.192/32`、`--record-cipher aes-256-gcm`→Rust cipher3、签名Wintun实际/32、outer1460→inner MTU1389；Linux同server bob/carol/dave/erin四独立IPv4与ChaCha/AES128/AES256 | **PASS_SCOPED** Windows自动+Linux异构真实受保护配置和OS；未验双Windows同宿主路由/同账号两个设备 |
| 真业务150s | Alice UDP C2S113657/113657、S2C113661/113661，TCP144双端；Bob113662/113662、113661/113661、TCP147；Carol56830/56830双向、TCP143；Dave56830/56830双向、TCP145；Erin113662/113662、113661/113661、TCP143。TCP invalid0；每端最大活跃UDP空洞不超过60.48ms | **PASS_SCOPED** kernel socket双向UDP+TCP五客户端全场；UDP合计909284首次唯一到达、TCP双端记录1444帧；不以成功包p99冒充残损/队列年龄（未测） |
| Stop | Windows自身WAL/Rust退出、真实server echo始终存活；Alice Stop后Bob额外4 UDP回声、Linux四客户端及server Stop；server TUN `routed=456217 unrouted=0 backpressure=0 reader_joined=1`、所有队列drop0；Windows WAL留存0、WSL bridge与netem恢复、Npcap cleanup PASS | **PASS_SCOPED** 真五客户端和共享OS生命周期；同Windows物理宿主双Wintun独立Stop仍H1587 FAIL |
| 容量边界 | 单程200ms、0%丢包、宿主4逻辑vCPU/2核；实际**outer双向总量**典型151.96Mbps，CPU整体忙碌末段最高92.6%，late速率跌至约123Mbps，host可用RAM低点10.638GiB | 五端功能PASS，后续同宿主250–300Mbps重L2/600s不派发；**容量CAPACITY_LIMITED，未测每worker/进程RSS及队列p99**，不能判产品/宿主根因 |
| 报表资格 | `qualification_scope=TRUE_150S_FIVE_CLIENTS_NOT_600S`；原strict `600s_outer_capacity=NOT_RUN_H1565_SHORT_FIRST_FAULT`，H1594最小修正后新报表会写`NOT_RUN_H1581_TRUE_150S_FIVE_NATIVE` | **150s业务PASS_SCOPED**、600s/30%五客户端业务/L3/GUI真实人机均NOT_RUN；报告字段修正不需要重测已经合格的原始产品 |

硬失败阻断H1587：每个Wintun原生plan都申请两条Windows全局`/1`捕获与同一TLS服务器物理`/32`逃逸，`native_unified_stage_routes_windows.go`保留精确owner CAS，不能借共享路径误删前一实例。复用当前架构没有已验证按进程/源IP隔离的Windows路由域；此处不为刷绿引入029/030服务或禁掉保护。PLAN028仍 **IN_PROGRESS**，L1必要额外组合及可独立量测的L3尚未全部完成。
