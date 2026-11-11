# M0 PLAN028 H1580｜2026-11-11中断恢复、原生Windows auto/cipher接线、治理/报表修复及待验门

**PLAN028：IN_PROGRESS。**工作在 `main`，不将源码编译/夹具恢复/旧SOURCE业务局部PASS冒充完整交付。恢复前主线 `7ee5c5fc20ff9b0dcd848905b496c8e2e14436f7`，现有候选代码提交 `813e4c5c71fe2a1f2442bfda0ce19c205a398d03`。长期原则与出口见 [覆盖及配置表](../../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md)，并按 AGENTS/PLAN028_INTEGRATION_ACCEPTANCE 执行。

## 先收的运行事实与原失败（无删改）

- H1576老Source `c3e60772c2f99e5d7fa1cadb0284b3e1addca1d4` Action `42979705842` overall **FAIL**，native Windows+四Linux真实UDP/TCP/独立Stop后兄弟继续/服务端Stop `PASS_SCOPED`；早期回声服务提前退出造成外部验证失败，应分离产品及夹具。
- H1577旧 Source `cd5dfa3b7688167eebfc12020e0180a9fa8df8f4` Action `42983815178` overall **FAIL**：原始 stdout `H1577_REAL_FIVE_OS_APPS_115PCT_OFFER_RATE_TRIGGERED`、`H1574_TRUE_FIVE_NATIVE_150S_UDP_TCP_CLIENTS_VERIFIED_PASS`、`H1574_REAL_150S_FIVE_TRUE_TCP_UDP_AND_EXACT_ALL_SIX_OWNED_STOP_PASS`、server `V4_PUBLIC_SHARED_TUN_STOP ... routed=524444 ... reader_joined=1 queue_full_drops=0`；最终 `H1548_FINAL_ORIGINAL_REAL_ONE_WIN_FOUR_LINUX` status `PASS_SCOPED_H1565_WIN_FIRST_THEN_FOUR_ORIGINAL_LINUX_LOSS0_200MS`，`Windows_original_WAL_leftover=[]`、WSL bridge/netem recovered。随后工作流尝试复制未生成的 `result/wl-public/normal-report.json` 才失败，历史失败不能抹。修复后的H1548脚本仅在**完整150s且真app/Stop最终PASS**时写带 `TRUE_150S_FIVE_CLIENTS_NOT_600S` 的兼容报告，40 echo短探针不冒充600s。
- 上轮 governance maintenance `42984484136` FAIL 12 个老断言；`42987330788`又因旧 H1566/1570/1571 文本门 FAIL 3。修正精确状态和 Frozen 55 操作（原54基础另有peer-persona校验）后 `42987762293` **SUCCESS**。旧Failure继续保留。
- 原30% Windows2025 200ms one-way 冷TLS问题此前 SOURCE620 真实握手超时。H1579 Action `42984484582` 预检FAIL，不等于新30%场景真正执行，更不能据此否认或声称修复；待以修复版单场真实复验。
- `42987762872` 来源 `813e4c5c...` Windows WAL **FAIL**：Windows Go 原装配、真实 native 包/单元测试已经PASS，最后脚本仍断言 `FixedPolicyForClient(1,0)`（过期PLAN022文本）而失败。现已把旧门更换为包含off/fixed/auto、Game、受保护租约/cipher及OS计划的source-only门；下一SOURCE Action需核真实结果，不能追认为813全绿。
- `42987762190` feature-catalog FAIL 是前次原生配置改动漏写 `feature-impact`，不是编译错误；本devlog与功能卡补声明，下一main governance须再核。

## 本轮有依据的实现及入口（提交/文件）

1. `5791668392b23c712ffc0943cab2d9bb23fedb18`：修10个治理回归旧文本门，保留真实改变过的报告/冻结 manifest。
2. `37f2c8fcbd517a4977e4fd0cbdf71427f3687855`：Windows `m0_native_v4_dispatch_windows.go` 增 `AutoLease` / `RecordCipher`，原Go固定 donor `cmd/wbd-client/main_windows.go` 经 `manifest-plan020-m0.json` patch默认 `--native-v4-product=true` 并传入原TLS policy；Normal Off/Fixed/Auto及Game2/4都改走每客户端 cipher 和 protected `AutoLease`，根据 `AuthenticatedLeaseIPv4()` 与 `ColdSnapshot().Cipher()` 核实际协商后，自动IP校验 /32 后传给既有 Wintun/OS WAL；Game组每lane必须保持相同租约/cipher。Rust仍稳态，未发明协议或Go packet pump。新增 `tests/test_m0_plan028_h1580_windows_auto_cipher_source.py` 和H1577报表修正。
3. `813e4c5c71fe2a1f2442bfda0ce19c205a398d03`：Windows Go 真实编译发现 Game `makePlan` 闭包还保持零参（旧Action `42987330429`、`42987330459` FAIL），修成 `func(verifiedLease netip.Prefix)` 并**使用TLS确认的 lease**装配Plan，不仅改变变量；同步 `m0_native_v4_windows.go` 与 `m0_native_v4_game_windows.go` fmt格式、manifest pins；修H1566/H1570/H1571 stale asserts。
4. 当次文档修复：Windows正式 WinForms `windows/gui/MainForm.cs` AES标签更正为“V3已验；V4原生待验”（通过唯一正式manifest exact overlay patch），既有 `lease4` 留空/显式 `/32`、`mtu=1460`、三种cipher和FEC表单由 `windows/gui/fields.json` 进入 `Portable.Effective→JSON→原Go --config`。界面入口显式 `--native-v4-product`、CLI默认native，不偷偷退回旧入口；GUI配置成功不是OS Applied。

**未改默认：**外层完整 IPv4 IP MTU1460B（1500只显式）；内层 Rust封装派生与真实OS读回；FEC默认Off、record默认ChaCha；Linux轮换间隔0，Windows rotate-min/max 0/0、keepalive15s/dead90s、idle-dormant0；outer repair on 为外观性机会式而非业务保障。未扩展029域名DNS/填充或030服务。

## 已复验、尚未验：逐 SOURCE 与实际 Action

| 证据 / Action | SOURCE | 结论（限定范围） |
|---|---|---|
| `42987762859` Windows Go & Rust + Linux Rust编译（初始平台job），原始 donor/M0 exact assembly | `813e4c5c71fe2a1f2442bfda0ce19c205a398d03` | platform compile/unit **PASS**；不能当Win新 auto/AES 驱动IO。构建 artifact digest 查看本次 [覆盖表](../../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md)。 |
| `42987762189` H1546 Linux ARM64 11文件 native Go/Rust/ISA-L production build | 同上 | build **PASS**，ISA-L实际backend/每binary hash从receipt取，不冒充arm长期流量 |
| `42987762119` H1376 | 同上 | x86_64与ARM64两个真实原Go TLS443/Rust共享TUN账户绑定**手动IP**独立业务及A退出B继续，原生Stop `PASS_SCOPED` |
| `42987762125` H1383 | 同上 | 双平台错误密码/原账号绑定拒绝，既有活跃A/B不受伤 `PASS_SCOPED` |
| `42987762898` Game4 overlapping native x86 | 同上 | A→A+B→B、新路径MTU、TLS无private前缀、Rust共享TUN及GameFEC `PASS_SCOPED`，Win新cipher不在范围内 |
| `42987762319`, `42987762229` | 同上 | Windows源锁定双owner槽/冷路径单元 `PASS`，非真实全链 E2E |
| `42987762909` | 同上 | 标准预共享route-keyTLS wire x86 **PASS** |
| `42987762293` | 同上 | 治理维护回归 **PASS**；基本feature-catalog曾FAIL缺日志，随本次一并补 |
| `42983815178` | `cd5dfa3b7688167eebfc12020e0180a9fa8df8f4` | 原始Windows+4Linux 150s双向 +全员Stop `PASS_SCOPED`，整体Action FAIL report；不算SOURCE813网络资格 |

本轮修改认证、租约、每lane配置，在最终 Windows signed Npcap/Wintun真实 auto/manual/3 cipher、同账号异参和TCP/UDP/Stop/路径变化、150s容量代表回归前不能将PLAN028标COMPLETE。既有 ARM64 30min及老 Linux弱网按不受改动组件复用，不刷矩阵；真实高损首先看冷TLS与服务器容量。过程中的 runtime 出错要修产品，不因VM或报告 FAIL 草率归因。

## 可接续下一步

收最新 main `governance` 与 Windows WAL/编译、读取本轮 Artifact 内的原始 file SHA256/backend，修有实据的失败。用现有真实 signed Windows test workflow增 **一个** auto+三cipher异参同账号客户端和Linux共享server的有界原生TCP/UDP、/32、Rust Cipher、OS MTU、owned Stop场景（缺必要证据不得宣告通过）；可将不同独立场景分不同Action，切勿重复派发正在跑的Job。随后按计划做真实30% coldTLS最小场景与Lifecycle、代表L3。保留每个原失败报告；收口表见覆盖文档。

```feature-impact
{"kind":"updated","ids":["record-crypto","windows-native-transport","gui-config-feedback","idle-rotation-keepalive","arm64-targets","normal-off","path-mtu-budget"],"reason":"恢复漏记的M0 PLAN028原生Windows默认入口、AutoLease/三AEAD真实传递点与新SOURCE验收限制；同步Linux/Windows/ARM64装配、1460/Off/Health默认、旧失败与新覆盖；旧证据均按精确SOURCE范围保留。"}
```
