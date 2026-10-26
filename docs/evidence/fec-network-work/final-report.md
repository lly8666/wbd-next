# FEC-only 独立岗位｜2026-10-26 限域合并审查索引

**2026-10-26 W111–W113 用户指定继续 GameMode fixed 测试（此节为最新 Game 结论）：GameMode 不需要 Auto，明确移出 Game 范围，Normal Auto 不变。** 真实 exact native `e8b41fb49a74648e405bf23e4600e23c618596fe`、build [40260662919](https://github.com/lly8666/wbd-next/actions/runs/40260662919) 的同一 frozen aarch64 二进制复用三个独立 Action（每个一个测试VM/一个性能job，`--outer-repair=off`、fixed6，未改 Rust/Go 产品算法，1Mbps/方向低负载、75ms 单程）。源/原生读数、每一条原失败、ZIP SHA256/CPU/RSS和 Gate 见 [W111–W113 机器收据](20261026-W111-W113-original-Game-fixed6-outeroff-bounded-ARM64-results.json)、[行动日志](../../devlog/fec-network-work/20261026-W111-W113-original-Game-fixed6-bounded-actions-intent.md)。

- **W111 Game4 真静默恢复 [Action 40268464615](https://github.com/lly8666/wbd-next/actions/runs/40268464615) `SUCCESS/PASS_SCOPED`**：双向1Mbps原 TCP+UDP active18s→12s `probe_hz=0` 无业务→resume15s，前后两向真 TCP/UDP各零缺失，resume p99 UDP/TCP ~77.5ms；安静阶段 injected=0，p99 null 无需虚造。两端 native `repair_enabled=0`、真实 DATA retrans0，parity planned=sent `17666/17674`、retained0/expired0、Stop 正常；测量 CPU client/server 3.07/3.15 CPU-s，RSS39.49/39.18MB，宿主 PSI peak2%。不能宣称已故意丢最后一组FEC量子或连续10ms跨业务HOL。
- **W112 Game2 fixed6 共享长 GE 严格1%业务门 [Action 40268468985](https://github.com/lly8666/wbd-next/actions/runs/40268468985) `FAIL`**：clean15→30s同 root `gemodel[3,17,100,0]`→clean15，双向各1Mbps、实际 UDP C→S **250/5515=4.533%**，S→C **238/5515=4.316%**；小UDP **2.484%/2.867%**，严格双向业务门均失败；无损前后 UDP各0缺失，所有 TCP 提交/送达、无回压，高损 TCP p99 **742.8/369.2ms**。两端 native FEC parity planned=sent `33285/33305`，recovered candidates `654/607`（不可直接等同已交付重建），outer DATA retrans0，sourceTUN/root drop0、native FEC invalid/conflict/codec/capacity/expired0，Stop干净；CPU3.84/3.82s，RSS26.59/25.92MB，宿主 PSI peak0.56%。保留 `FAIL`，不得重标为 clean gate PASS。
- **W113 Game4 fixed6 相同类型共享长 GE [Action 40268472555](https://github.com/lly8666/wbd-next/actions/runs/40268472555) `FAIL`**：C→S **49/5516=0.888%**（该方向过1%门），S→C **58/5516=1.051%**（该方向失败）；小UDP **0.287%/0.573%**，前后 clean TCP/UDP无缺失，真实 TCP 高损全到/无回压、高损 p99 **333/125.5ms**。native parity planned=sent `33345/33350`、recovered candidates `539/541`、outer DATA retrans0、sourceTUN/root drop0、native FEC reject/codec/expired0、Stop干净；CPU6.30/6.36s、RSS39.20/38.22MB、PSI peak1.2%。**不能说 Game4 双向严格1%业务通过。**

**诊断边界**：三条为不同 Actions/虚拟机、GE 轨迹未固定，不能把 Game2/Game4 的差异宣称同机 CPU 因果或与 W102 历史3Mbps来源作真实算法回归/改善比较。host PSI 均不高、实际 parity 全发送/outer DATA0、原 TUN drop0，支持不是本轮明显宿主限速，但没有 per-block timely erasure 证据证明存在可解码漏交付，**先不改编解码/不重写外层**。保持 `capacity_stop=true`，`merge_ready=false`；继续限域审查 `scoped_integration_review_ready=true`，Windows TEMP_SKIPPED 不变，**Game Auto 已由用户排除、不再列为缺口。**

**2026-10-26 W110 之后的最新远端复核入口（优先于下文 2026-10-25 W83 历史索引）：** [Git/Actions 逐项审查、精确原始产品与限域合并边界](20261026-post-W110-git-actions-scoped-merge-audit.md)。最新已验证 Game/Normal 公共 Go TLS/FEC 原始 ARM64 二进制源为 `e8b41fb49a74648e405bf23e4600e23c618596fe`（构建 [40260662919](https://github.com/lly8666/wbd-next/actions/runs/40260662919)，artifact `12623678360`），当前分支证据提交在此之后不修改 Rust/Go 产品数据面。W103–W110 分模式限定通过，W102 更早 SOURCE 的共享长 GE 2.43–2.56% 仍是风险，**不是 e8 上的新长 GE 通过**；Game Auto/Windows/物理机/FEC+outer ON 仍未认证。保持 `scoped_integration_review_ready=true`、`merge_ready=false`、`capacity_stop=true`，不加压、不合 main。旧历史源码、失败 Actions 与反例不得删改。

**当前交付状态：** `scoped_integration_review_ready=true`；**`merge_ready=false`，`capacity_stop=true`**。以下只为已跑原生 Linux ARM64、真实外层 DATA repair OFF 的 FEC 功能/业务性能**限域审查**，不是全平台、不是与 main/新外层 ON 组合的整机合并资格。入库前的证据审查基线 `084e7215f48c0d96a55b92a5a3691aa346dcdda2`（2026-10-25 12:17 UTC，W83 文档收口）；后续源码或分支变化必须重新核证，不能把 HEAD 直接当作已运行的产品二进制。

## 精确产品与证据索引（旧时点记录保留在后文）

- **近期真实 FEC-only 产品源码：** 冻结 `7ad0ba91b656ff8e9ee965d0c093a18e048971fb`；原生 aarch64 [build 40185113624](https://github.com/lly8666/wbd-next/actions/runs/40185113624)，artifact `12596370712`，ZIP SHA256 `ab1407ccc5dd85c3a66c885cd410dbdd27fa7059461f18647d8ca6b41ce7384e`。W77 与 W79–W83 独立场景复用这同一产品，**各 Action 一个 VM/测量 job**；W83 在同 VM、同进程顺序比较长/短相关丢包。W78 的 `4a77104b` 是额外 native **测试专用** fence 构建，不能擅自把它当作 W83 产品。
- **开关与反馈：** 上游 V3 为基底，公开 `--outer-repair=off` 的两端 native readback 和受损时 0 外层 DATA 重发/候选/shadow 已验证（W2/W6 及后续），默认 ON 保护由 W6 同 VM 正反例验证。OFF **未关闭首次 DATA、FEC parity 或认证的原始 M2 回执/质量反馈**。真实 native Fixed/Auto requested→applied、parity planned=sent、recovered-to-TUN、原 TUN 源丢失和资源上限均有独立证据；不以 netem 线损代替 Auto 质量。
- **固定与成本：** W3/W5/W51/W58–W59 的真实固定档、双向首次交付、恢复与低中强档代表通过限域门；W41/W42 是 Maximum 30% IID/300ms、双向各100Mbps混合流量的同 VM AB/BA 正向收据（测量 CPU 相对降低约21%，有 VM host PSI 混杂，不能泛化）；W46/W47 是 Normal/off 与 Fixed3 小流量同 VM CPU 保护；W77 覆盖真实奇数包长、reorder/duplicate、健康 TCP，以及 old revision fence W78。相关原始 CPU-s/RSS、p99、流量分母和容量约束必须读下文原始表，不将不同 VM 相除算提速。
- **自动控制：** W45/W52–W56/W60 已记录原生双端认证 M2 控制/上下行独立升降档与恢复改进，W61–W76 覆盖本机过载 host-capacity 样本、保护与解除后的 native APPLIED；最新 W81 真正 VALID 的 C→S 强升至 Maximum6 再逐级降到 Light0，两端 native `requested=applied` 且 `pending=false`。**W81 高损过渡 C→S 3.049% 残余允许用于控制验证，但不是 1% 业务服务通过。** Auto 未验证的远端持续接收机过载，不能假称被本机保护覆盖。
- **相关丢包反例和边界必须保留：** W79 Medium2 的约5% GE 长突发 residual **2.849%/2.798%**，Action 绿仅是宽诊断门；[W80 40191030800](https://github.com/lly8666/wbd-next/actions/runs/40191030800) Maximum6、约15% GE 较长突发 **1.341%/1.531%，严格1%门失败**。W82 较短突发同约15%均值 **0.162%/0.219%**，W83 相同 VM/进程先长后短 **1.321%/1.303% → 0.215%/0.200%**，短段严格门通过、长段未通过。该有限统计与计划/发出 parity 相等、native reject0、源 TUN drop0 一致，**不证明有可及时解码却漏交付的 codec 缺陷**，不应因此臆造重传或调整 FEC 算法。详情及 Action/attempt/artifact/hash 在 [W79–W83 原始收据](20261025-W79-W83-GE-correlated-burst-original-arm64-SCOPED.json)。
- **W84 既有原生 Actions 产物复核（无新负载/无补丁）：** 将 W81 C→S 约60s长相关突发按 10ms 应用收发分桶加传播偏移重算：突发前30s（Auto从 Balanced3 升到 High4 并到 Maximum6 请求）缺口约 **4.90% / 2162包**；后30s（Maximum6 请求已发，原生每 revision 精确 APPLIED 时间未记录）约 **1.24% / 546包**；内部稳定 20–24s 约 **1.35%–1.48%**，敏感性验证仍超过1%。故原整段业务 cohort **3.049%** 主要归于可接受的升档过渡（分桶缺口约80%），**仍有约1.3%–1.5%的最高档长 GE 残余**，与从头 Fixed6 的 W80/W83 **1.30%–1.53%** 一致；短 GE 约0.2%仍通过。真实 parity 全发送/outer DATA0/TUN source drop0/native reject0，未定位可恢复但漏交付缺陷。W81 PSI 有短暂峰值，不代替 W80/W83 低 PSI 对照。基于有限 MDS/长相关擦除限制，不针对可接受过渡调 Auto/重写 codec；若未来此长 GE 也必须≤1%，先补逐块有限 erasure 与 TX 发送时序证据，再同机比较不加 parity 的错峰/交织，保证源首次交付、TTL、CPU。完整逐窗/不确定性见 [W84 原始重算收据](20261025-W84-W81-auto-transition-vs-Maximum-plateau-artifact-reanalysis.json) 与 [W84 devlog](../../devlog/fec-network-work/20261025-W84-auto-long-GE-plateau-from-existing-Actions.md)。
- **W85 两组已就绪 parity 交织：候选原生通过、真实同 VM A/B 负结果、已撤回产品补丁。** 在冻结旧产品 `7ad0ba91` 与新候选 `7cb64bfc` 的 ARM64 原生正确性通过后，[W85b Action 40202359496](https://github.com/lly8666/wbd-next/actions/runs/40202359496) 同一 VM 依次 A/B 测约15%长 GE（双向8Mbps、96% UDP、2路TCP、75ms、outer DATA OFF）：A C→S/S→C UDP **1.325%/1.198%**，B **1.390%/1.194%**，双方均严格超出1%门；小包/p99未出现有证据的总体改善，client/server CPU-s A 15.56/15.41、B 15.45/15.41，每有效GiB CPU成本近似持平；RSS峰值约23.1/23.3MB，B宿主CPU PSI峰32.21%混杂。虽 B 发生 genuine 修复交替，client 2598/212653≈**1.22%**、server 2346/212684≈**1.10%** 修复行实际参与交替，双组同时 ready 占比过低；所有 parity 正常发送、原 source TUN drop0、RX reject0、outer DATA0、正常阶段业务缺失0。依据“不等待凑组、不扩至更多组/不增加修复、收益不足撤回”的明确停止条件，恢复 `v4_fixed_stream.rs` 与 `v4_embedded_go.rs` 的 W85 前精确源码 blob；历史负例、不达标门槛及候选 commit 仍保留。原始产物 artifact `12601699742` SHA256 `6c7c388eb00d3babf93897d12333c5dbeef4d4b71d86d493b9a54a6c0ec4fea8`，参见 [W85 原始负结果收据](20261025-W85-two-ready-parity-interleave-sameVM-AB-NEGATIVE-ROLLBACK.json) 和 [实施/回撤日志](../../devlog/fec-network-work/20261025-W85-two-ready-parity-interleave-implementation-and-Actions.md)。未增加 B/A、短 GE/ IID/高负载 Actions，**不能宣称这些已经在候选代码上通过**。
- **W86 用户暂跳 Windows 测试及后续 Linux 行动：** 依最新指令，仅 **本 FEC 工位** 的 Windows x64/native FEC2 codec/ISA-L、Go/Rust 原产品、Wintun/GUI/打包、Windows Game/生命周期验证统一标记 **`TEMP_SKIPPED_USER_20261025` / `NOT_RUN`**，不是通过、不是永远取消，也不修改 M0 的 Windows Actions/源码/进度。复测须用户解除后按最新 Windows 原生产品独立取证；Linux ARM64 绝不能顶替 Windows。上述暂跳、W85 原残余 1.2%～1.4% 且交织仅1.1%～1.2% 的未解决边界、真实 FEC TUN 65KiB 当前不支持、远端 RX 宿主信号、历史混合 TCP 100Mbps 回压、最新组合 outer ON 均归档于 [W86 状态收据](20261025-W86-windows-temporarily-skipped-and-linux-priorities.json)。**Linux 后续 W86** 有限验证只以回滚旧源码 `4322a811` ARM64 [构建 40203220219](https://github.com/lly8666/wbd-next/actions/runs/40203220219) 对照历史 W50 的 100Mbps 回压，单独运行 Fixed Balanced3 双向8Mbps mixed TCP/UDP IID10→30→10%、300ms 单程，守住 source TUN、M2/outer OFF、1%低损恢复门；**真正 [W86 Action 40204401717](https://github.com/lly8666/wbd-next/actions/runs/40204401717) 结果 INCONCLUSIVE/Action FAILURE：** 8Mbps 下 IID30% 高损真实 TCP 注入仅 C→S/S→C **0.146/0.155Mbps**（目标均0.320）、p99 **21.48/16.94 秒**、回压2186/1233次；即使回到10%，S→C仅0.277Mbps、179次回压，C→S0.309Mbps。机器 CPU PSI peak仅0.42%，有认证 M2、parity planned=sent、outer DATA retrans0、TUN/source/root drops0、RX容量拒绝0；服务端实际RX冲突/解码拒绝各1次**不能记为零**。UDP恢复10%阶段缺失仅11/19，小包p99约316.3ms，**低损UDP通过不等于TCP恢复通过**。精确 ZIP artifact `12603890171` SHA256 `785c061807f17df193121bed8c8621bf575614d8bdb45329f6f0465518721f3c`，见 [W86 原生负结果](20261025-W86-balanced3-8m-TCP-highloss-recovery-INCONCLUSIVE.json)。因为高损内层TCP也可能受 Fixed3 FEC 保护不足影响，只加一条同负载 Fixed Maximum6 8Mbps [W87](../../../tests/network/fec-work/W87-maximum6-8m-TCP-recovery-original-arm64.json)：[W87 Action 40204822076](https://github.com/lly8666/wbd-next/actions/runs/40204822076) **SUCCESS/PASS_SCOPED**，同一产品源码 Fixed Maximum6 双向8Mbps，高损 IID30% 主 UDP 缺 31/82430 与 59/82430（0.0376%/0.0716%）、TCP双向实际持续约0.320Mbps、p99 1039.8/993.7ms、回压0；回到10%后 TCP各0.320Mbps、p99 315.3/316.4ms、回压0、UDP缺0。native两侧 requested1=applied1 profile6，parity client256497/server256699 均 planned=sent，原 outer DATA0，源 TUN0、RX capacity/codec/conflict0、实际 FEC recovered TUN client37771/server37856。120s client/server CPU-s **15.97/15.96**、RSS peak 23.07/22.99MB、host PSI peak1%；真实 artifact `12603069627` SHA256 `6c3ab1777a400601671cc6c30ac504503aab936391a5b77253284b5062fae6fd`，详见 [W87 8Mbps Fixed Maximum6 原始收据](20261025-W87-maximum6-8m-TCP-highloss-recovery-PASS-SCOPED.json)。**W86/W87 是不同 VM、非同随机 GE/IID轨迹的不同 profile，没有同机CPU相对收益因果资格**；可以限域判定此低负载高 IID30% 下 Fixed6 保留内层 TCP 推进，而 Fixed3 不足，但**W49/W50 100Mbps 的高载问题未复验/未修复**。
- **W88–W89 Game2/Game4 公开原生 Linux ARM64 有限 GameMode 资格：两模式已测，Game+FEC仍不支持。** 当前公开 `game2`/`game4` 仅原 Go TLS 认证多 lane 复制+去重，`game_fec=off`；现有公开CLI没有 Game+FEC，Game不能伪装已经通过 Normal 单lane `--outer-repair=off` / authenticated M2 recovery 字节账本（真实结果中的 `NOT_APPLICABLE_GAME_MULTILANE`）。复用**精确原生产品** `4322a811`（[build 40203220219](https://github.com/lly8666/wbd-next/actions/runs/40203220219)）；四次独立真实原生 Actions **均 PASS_SCOPED 预先限定的 native/无损门**，每次一场景/一个 job：
  - **W88** 各lane独立 IID20% (3Mbps/方向、75ms单程、UDP96%+2路TCP) [Game2 40206528368](https://github.com/lly8666/wbd-next/actions/runs/40206528368)：C→S/S→C UDP **3.984%/4.129%**；[Game4 40206531539](https://github.com/lly8666/wbd-next/actions/runs/40206531539)：**0.194%/0.139%**。Game2 无法满足这一高损期1%门，别把 Action Clean门绿写成全段成功。第1lane黑洞且其他 lane 健康时 Game2 C→S **2/16513** 缺、S→C零缺，Game4 两向均零缺；TCP实际继续送、无回压。Clean前后两模式双向 UDP全收；native copied/delivered 两端真实、auth_rejected0、TUN/root drops0、Stop干净。Game2宿主 PSI 短峰 **34.98%**，不能跨VM拿其CPU与Game4相除求严格因果开销。[W88 全部收据](20261025-W88-original-Linux-Game2-Game4-independent20-lane1-blackhole-PASS-SCOPED.json)。
  - **W89** 共用单一 root `netem gemodel [3,17,100,0]` 长GE，~15%共享线路损伤，[Game2 40206930859](https://github.com/lly8666/wbd-next/actions/runs/40206930859) C→S/S→C UDP **13.355%/13.149%**，[Game4 40206935735](https://github.com/lly8666/wbd-next/actions/runs/40206935735) **8.312%/8.566%**。**这两种模式在共享长相关丢包期间均明显不达1%业务目标**；Actions `PASS_SCOPED` 只代表原本预声明的 Clean端点与 native/Stop 门，绝不是共享 GE 服务通过。TCP两向业务最终连续注入并送达，高损 p99 Game2 **2.79/2.35s**、Game4 **0.65/0.62s**，恢复清洁段双向UDP缺0。全程无源端 TUN/root丢、无认证拒绝；每组成本详见 [W89 原始收据](20261025-W89-original-Linux-Game2-Game4-shared-GE15Long-SCOPED-HIGHLOSS.json)。
  - **综合边界：** 两种公开 GameMode 的低负载 Linux 原生功能/独立lane故障/清洁恢复已拿到限域产品证据；共享长相关损伤仍很弱，不能用独立lane `p^L` 套入共同突发。Game+FEC联合算法/Windows Game/outer repair OFF for Game/真实主机容量与跨VM严格CPU效益 **未通过也未被本轮实现**。Windows本工位仍 `TEMP_SKIPPED_USER_20261025`，M0的Windows代码/CI保持不变，`capacity_stop=true`、`merge_ready=false`，不合main。完整 [W88/W89 日志](../../devlog/fec-network-work/20261025-W88-real-Linux-Game2-Game4-scope.md)。
- **W90 Game2/Game4 与 FEC2 联合接线尝试：原生功能验证成功、真实业务六条 FAIL、候选已原子回滚。** 用户本轮授权 Linux 公开 `--game-fec=fixed0..fixed6`（仅Game2/4，原Go TLS保护请求/响应严格协商）、原Game每lane AEAD/PN 后叠已有FEC2 M3、source首交、parity及同一原生 TUN/Stop。精确 Rust/Go ARM64 构建 [40209693209](https://github.com/lly8666/wbd-next/actions/runs/40209693209) 和修订后一修复只走一条轮转 lane+先源 M4 [40211176601](https://github.com/lly8666/wbd-next/actions/runs/40211176601) **都通过** Native Go TLS mismatch、Game2/4原生缺源恢复/Go/Rust/ISA-L/Stop；这只是组件正确性，**不是产品业务通过**。真实 Linux 3Mbps/方向、Game2/4 Light0 或 Maximum6 的六次测试均 FAIL：[Game2 fixed6 40209948309](https://github.com/lly8666/wbd-next/actions/runs/40209948309) 和 [fixed0 40210447377](https://github.com/lly8666/wbd-next/actions/runs/40210447377) 以及 [source-first one-lane修复 40211434490](https://github.com/lly8666/wbd-next/actions/runs/40211434490) **内层TCP连接设置阶段超时**，甚至未进入网络损伤阶段；Game4 [fixed6 40209953632](https://github.com/lly8666/wbd-next/actions/runs/40209953632)、[fixed0 40210452663](https://github.com/lly8666/wbd-next/actions/runs/40210452663)、[source-first one-lane 40211439531](https://github.com/lly8666/wbd-next/actions/runs/40211439531) 虽有原生认证后FEC恢复候选（例如末版 client627/server521），但**无损阶段实际UDP就大量缺失、TCP回压、原M4发送失败/接收拒绝多，远超原1%门**。末版Game4 CleanBefore C→S **4753/6869**，原生 repair `rplanned=16355/16378` vs 真核 `rsent=15162/15211`，未全部送达；`host PSI peak2%` 不能推断资源无瓶颈。**不放宽历史门、不把FEC候选恢复数当实际交付、不宣称Game+FEC已接通。** 所有尝试与hash详见 [W90 终局负例](20261025-W90-GameFEC-product-candidate-FAILED-rollback.json)、[开发原生验证/回滚日志](../../devlog/fec-network-work/20261025-W90-game2-game4-fixed-FEC-wiring-and-native-validation.md)。因候选在 clean/基本 TCP 都失败，`b5052654975b4c3aa33fdabcb90d0e0803768315` 一次 Git tree commit **16路径原子回滚**15个本轮修改文件与新增`v4_game_fec.rs`，核对原 blob 与 W90 之前 `d4759a1d` 逐字节一致；留存失败提交、Actions、测试配置/报告。原生回滚核验 [40211941478](https://github.com/lly8666/wbd-next/actions/runs/40211941478)/ [40211941508](https://github.com/lly8666/wbd-next/actions/runs/40211941508) 结果另按真实完成记录。最终用户可用状态依然是 **Game2/4纯复制限域通过，Game+FEC不支持**；非Linux/Windows仍按本岗位TEMP_SKIPPED，`merge_ready=false,capacity_stop=true`，不碰M0 Windows、不合main。
- **未覆盖/不能合并成全绿：** 真实 FEC-over-TUN 65KiB 产品、Windows/Game 产品接线、远端接收方持续 host 过载反馈、W49/W50 历史100Mbps TCP 高损后恢复、和**精确最新组合源码上 outer ON+FEC** 均未拿到本岗位代表资格。W38 混合200Mbps已有源头丢失/TCP 回压负例，故依约停高压，不再无意义扩梯子。W86/W87仅新增有界8Mbps低负载测试，不接管外层恢复实现、不改其他岗位进度、不合 main；不再升级任何宿主负载。

**复核结论：** 当前可交付一份带正反例、核对过最新 Actions 单 job 与 artifact digest 的**限域合并审查包**；没有已证据支持的 FEC 算法小修复待做。审查者若需要扩大产品资格，应按未测项另建精确组合验证，不能复用旧 W3–W7 的 `b601f2e5` 二进制替代 W79–W83 的 `7ad0ba91`。以下是原有逐阶段原始报告，历史 SHA/失败/指标均完整保留。

---

## 历史阶段报告（保留其当时产品适用范围）

### 2026-10-24 初始 V3/b601 分阶段验收

**更新：2026-10-24。分支：** `experiment/fec-network-tuning`。**适用产品源码：** `b601f2e546bf5f071eb33a80a01beec71d91c5cf`，原生 ARM64 build Action [40078403217](https://github.com/lly8666/wbd-next/actions/runs/40078403217)、bundle artifact `12554277143`、ZIP SHA256 `552a9c19ca4b9045cabe08abeed4f80e440f73f8fcc34a5f06670f4450d9fde6`。以下实际产品运行 W3–W7 均复用这同一 SOURCE 构建的冻结二进制，夹具请求源码各自独立。

## 合并和边界

V3 双亲合并 [1a04e791](https://github.com/lly8666/wbd-next/commit/1a04e791d28d860107f31bcfe463846cf3f5c2ac)，第一父 `9cfd72968e21a63834f455a96afc71a5d35737db`、第二父网络冻结 `040741820b2f917b5868c285c438d4cc21c6193a`，共同祖先 `45325c9c965e56080f2035bafcf235aa02a1a6c0`。保留网络 V3 公共数据通道、机会式 DATA 修复、半量独立 frozen ciphertext shadow、首发 F 字节账本、批量预算、统一 MTU、真 TUN 与产品自有 fq600/flow_limit256；仅在原公开 Go CLI→bridge→native owner 实装 `--outer-repair=on|off`，默认 ON 不退回 v2。OFF 不建立修复候选和密文副本、不重发外层 DATA，但保留真实 M2/FEC feedback、DATA 首发账本、FEC source/parity 首发。Linux public Game OFF、Windows GUI/系统不在此次产品资格内。没有覆盖原网络岗位进度、请求或合并 main。

最小 Fixed/Auto applied 修复 [b601f2e5](https://github.com/lly8666/wbd-next/commit/b601f2e546bf5f071eb33a80a01beec71d91c5cf)：只将「整个 2s 观察窗零 UNKNOWN」的过严 *档位 applied 证明* 改为「原 M4 已复制 source+parity、同代际 revision，且有成熟 authentic unambiguous positive receipt、无容量审查」。UNKNOWN 与 censored 质量仍保留原义、不伪造成零损或 ACK。原生 ARM64 maximum-row/回执单测 [40078693263](https://github.com/lly8666/wbd-next/actions/runs/40078693263) 和 harness contracts [40078693315](https://github.com/lly8666/wbd-next/actions/runs/40078693315) 通过。

## 实测：功能及成本

| 场景（每个性能 Action 一个测量 job） | 两端真实 native/应用事实 | CPU / 内存 / 首次交付 | 资格 |
|---|---|---|---|
| W2 [40077795567](https://github.com/lly8666/wbd-next/actions/runs/40077795567)，旧合并 SOURCE `1a04` | Outer OFF 双端零 DATA retransmit/候选/shadow；FEC 确认交付 TUN 恢复 532/518；Fixed 一侧 `applied=0,pending=true` | CPU 1.87/1.94 CPU-s，RSS 约19.9/19.5 MB | **FAIL 原反例，历史保留** |
| W3 [40078693282](https://github.com/lly8666/wbd-next/actions/runs/40078693282)，Fixed5 0→5% IID，双向各2Mbps，单程25ms | 两端 `requested=applied=1`、pending=false、outer OFF/0 retransmit；Recovered TUN 521/519，IID5 应用缺失 0/0 | p99 41.3/44.3 ms；测量 CPU 1.66/1.67 CPU-s、RSS ~19.9/19.7 MB | **PASS_SCOPED** |
| W4 [40078980002](https://github.com/lly8666/wbd-next/actions/runs/40078980002)，Auto clean 各2Mbps | 两端 `requested=applied=1,profile5`，outer OFF，真正 parity 首发；无业务缺失 | p99 25.3ms，测量 CPU 1.03/1.03 CPU-s | **PASS 启动强档，不代表动态 Auto** |
| W5 [40079244149](https://github.com/lly8666/wbd-next/actions/runs/40079244149)，Fixed 最大档，真实IID30%/one-way300ms，双向各12Mbps、线路各50Mbps | 两端 profile6 applied1；outer OFF 0 retransmit；恢复并交付 TUN 27,035/27,247；C→S 缺57包，S→C 缺45包（业务残余0.081%/0.064%） | 首次到达 p99 315.3/315.2 ms；CPU 7.92/7.84 CPU-s，RSS 22.4/21.9 MB；无源 TUN drop | **PASS_SCOPED，高损代表容量足够，不加压** |
| W6 [40079302195](https://github.com/lly8666/wbd-next/actions/runs/40079302195)，Normal V3 ON→OFF，同 job/同 ARM64 VM 顺序 AB，双向各2Mbps、IID2% | ON 真实 repaired DATA 131/127、repair wire 147322/150339B，缺失 95/90；OFF 两端 0修复、0候选、0缓存，缺失212/182。两组各单独 TUN/Stop，无重复测量 job | ON CPU总观测 1.39/1.43s、p99 25.5/25.4ms；OFF 1.29/1.32s、p99 25.2/25.2ms。观测级同机比较，不作严格因果提速宣称 | **PASS 默认ON及真实OFF保护** |
| W7 [40079564452](https://github.com/lly8666/wbd-next/actions/runs/40079564452)，Auto 非对称 2/0→20/1→1/0%，双向8Mbps、单程75ms | high C→S缺10包（0.021%）、S→C缺0；TUN恢复 client511/server10929，outer OFF/0 DATA repaired。两端始终 profile5、revision1，无在线升降档 | high C→S p99 92.9ms；CPU 15.53/15.16 CPU-s；RSS ~21.3/20.7 MB | **PASS 业务/静态Strong，动态Auto FAIL/NOT_WIRED** |

所有总量都是原生 CPU/主机观测或应用收支，不把 CPU-s 等同单核利用率，不把净损伤率当业务缺失率；W6 AB 非复现同一损伤随机序列。Linux kernel fq600/flow256 的真实产品 owned TUN readback 由网络冻结点原验收及本合并后 harness 继承；W3–W7 未重新声称 Windows fq。

### W5 理论与完整性解释

按系统性 MDS 码、独立损伤和幸存分片及时到达，单源残余 `p × P[Bin(k+r−1,p) ≥ r]`。最大档真实发送 parity，理想 p=30% 时：`k=16,r=20` 为 **0.022826%**；`k=8,r=10` 为 **0.380782%**；`k=4,r=5` 为 **1.73903%**；`k=1,r=2` 为 **2.7%**。W5 每侧约 `5442` 个满组 `k13..16`，但另有 `k=1` 2501/2372 组，且小 partial 组不会有和大组同样的容错。实际确切 `k=2..4,5..12` 目前仅桶聚合，不能虚构精确逐 k 理论或用“收到的 r”替代发送 r。该场景实测双向残余小于 1%，不是理论零丢包。

## 未完成与平台边界——不得误标全绿

1. **Auto 真动态控制仍未接线（功能未过）。** Go `v4ProductFecMonitor.start` 在首次 mature ACK 后直接退出；W7 两端 profile5/revision1 在 20% 高损和降损后均不变化。不能因 W7 业务残余很小就宣称上行、下行独立 profile 升降档通过。下一实现须从同代际真实 firstsend mature windows、actual-k/host censor 形成可信 `FecV2Snapshot`、执行 2s profile 决策、在不撤销旧块的 quiescent 边界 stage 新 native revision，且双端真实 readback。已有 `fec_v2_runtime_controller.go` 与 `FixedStream::quiescent_change` 可复用；尚不能把线损 netem 值或 FEC recovery outcome 当伪样本。
2. **RTT 读回边界。** OFF 有真正 `V4_PUBLIC_FEC2_M2_PROOF.reverse_reports`，W5 client14735/server14773，W7 client29832/server25487；但是外层 shadow RTT `timing_samples=0,srtt_us=600000` 是关闭修复后的默认诊断，不是实际测得的 FEC-only RTT。需要独立真实 M2 confirmation-latency/RTT 低开销读回，不要为填数字造 shadow/cipher cache。
3. **确定性缺源恢复的合并 SOURCE 专项仍未复验。** Rust codec/stream 单测及 `r0/go_overlay/internal/realityfront/bridge_v4_live_fec2_kernel_linux_test.go` 有相关已存在的精确缺源、真 parity、内核 TUN 交付测试源；本次未在合并后 b601 对该专门确定性测试跑 Actions。W3/W5 是 *真实有损 FEC recover-to-TUN 正例*，但不冒充可复现指定某 PN 丢失。认证、generation、replay、MTU、Stop 均在当前公共系统约束内未削弱。
4. **未测试：** 多业务极限 HOL、Windows 产品、Game+FEC 动态、物理链路、未知更高单核容量边界、全 k 档逐组概率的精确对应；不再放大容量压力。原网络独立已知混合 RX 问题属于 COMMON_PATH、不能由 FEC 收据覆盖。

**交付资格：** 合并 V3、真实外层 OFF、Native Fixed5/Maximum 及默认 V3 ON 保护已形成可复用、可审查的单分支**限域合并候选**；**完整用户 FEC Auto 目标未验收，故整体 `merge_ready=false`，不自行合入 main。** 不应重复跑已通过的 W3–W6 或旧 `7ad7e0e1` 二进制。继续工作必须针对 Auto 真实观测/安全在线修订与独立 RTT 证据，而非原网络岗位 `next_action`。

## 2026-10-24 Maximum50 容量修复专项补充（Auto 仍未完整通过）

最新独立 RX source `ec344557fa8cbf4d717a81833d36f92584263478`：原生 ARM64 build [40087393299](https://github.com/lly8666/wbd-next/actions/runs/40087393299) + deterministic actual parity-to-TUN 单测 PASS；[W13 单场景](https://github.com/lly8666/wbd-next/actions/runs/40090193642) 真 50Mbps/方向 30% IID 300ms，双端 delivered49.985/49.990Mbps，残余0.0517%/0.0496%，native Fixed Maximum profile6 两端 applied，outer DATA repair=0，RX decoder reject0/0，FEC recovered TUN67115/66417，CPU12.54/12.67s、RSS29.7/29.6MB、p99 304.6/304.7ms，源 TUN/root qdisc drop0。RX bounded 96 blocks/8MiB，原 age150ms、reorder span128，峰值57/58blocks、约1.9MiB，Stop typed error counters齐全。[专项证据](20261024-W13-max50-scoped-PASS-and-W12-AB-boundary.md)。

**独立单次 W13 PASS 并不覆盖 [W12 同VM顺序 AB](https://github.com/lly8666/wbd-next/actions/runs/40089406842) 的 B 单向 C→S 12.23% FAIL**；后一收据含 client veth 286.9MB，W13 client326.3MB，虽两次 FEC RX 拒绝和 native M4失败均为零。顺序效应/本地出口节奏尚未归因，需另行验证才能声称全场景性能可靠。75Mbps历史失效依旧，100–200Mbps未测；Auto 真升降档仍未验收，保持 `merge_ready=false`、容量停止继续。用户要求暂时收口，本轮不再刷全绿或扩压。


## 2026-10-24：后续逐档 75→100Mbps 验收与硬容量边界

分支 `experiment/fec-network-tuning`，冻结新原生源码 `ec344557fa8cbf4d717a81833d36f92584263478`，ARM64 产品 build Action [40087393299](https://github.com/lly8666/wbd-next/actions/runs/40087393299) artifact `12558215058` SHA256 `bd22744ae29bcb0ec8b57cba9bdcc7b10228911e9af628791501ff7623b008d3`。沿用已真实 applied 的 Fixed Maximum profile6；双端 outer DATA repair OFF 且 parity 首发独立，双向 30% IID、300ms 单程、99% 1287B/1%64B、15s warmup+30s measurement+30s drain、每档一个 Actions 测量 job。线路 cap 取业务带宽4倍，是避免外线路自己限死高吞吐，不代表保持同一外网 cap 的吞吐曲线。原 W12 同VM AB 第二段本地出口丢量异常**仍未解释**，本报告为 standalone 观测，非连续运行保证。

| 每方向业务档 | 实际交付 C→S / S→C | 首次p99 | RX peak slots(客户/服) | RX pressure eviction(客户/服) | 判定 |
|---|---|---|---|---|---|
| 50 Mbps, netem cap200 | 49.985 / 49.990 Mbps | 304.6/304.7ms | 57/58 | 0/0 | W13 [PASS](https://github.com/lly8666/wbd-next/actions/runs/40090193642) |
| 75 Mbps, cap300 | 74.967 / 74.979 Mbps | 303.5/303.5ms | 83/83 | 0/0 | W14 [PASS](https://github.com/lly8666/wbd-next/actions/runs/40091124249) |
| **100 Mbps, cap400** | **99.956 / 99.968 Mbps** | **303.1/303.1ms** | **96/96（等于硬上限）** | **29,425/29,425** | W15 [业务 PASS、RX 容量触顶](https://github.com/lly8666/wbd-next/actions/runs/40094982877) |
| 125 / 150 / 175 / 200 Mbps | **未测** | — | — | — | **W15容量不足停止加压，不得编造** |

W14真实 75Mbps netem 损伤29.948%/30.011%，业务未到119/92包，FEC recovered-to-TUN 客户99625/服99396；RX peak bytes2.84/2.87MiB；客户/服测量CPU16.79/16.93 CPU-s、RSS34.44/35.10MB，宿主CPU PSI峰值14.33%，outer retransmit0、源TUN drop0、Stop drained。Action 产物 `12559275827` digest `b897193008c3203ca9014d826b27bc1a306261d1d7e298eb35c5db7ce819fad7`。

W15真实 100Mbps netem 损伤29.940%/29.855%，业务未到191/150包，FEC recovered-to-TUN 客131785/服132456，实际 parity 接收388371/388503；RX decoder_rejected0/0、reject_capacity0/0、拒绝Codec0/0；RX peak **96/96、pressure_evicted29425/29425**，内存字节峰值仅3.606/3.606MB（小于8MiB）。因此第一明确的硬容量是**活跃block槽位**；`pressure_evicted` 指本地旧组状态的容量性淘汰，不等于实际丢失了同数业务包（业务仍然PASS）。客户/服测量CPU19.40/19.54 CPU-s、RSS39.69/39.92MB、PSI峰17.76%；Source TUN drop0、外层 DATA 重传0，Stop drained。Action 产物 `12559509835` digest `877d3177d03268adc325aa1aa8b5e418d597c8d1ac223f9030671a683a721175`。

**结论：** 这一版 FEC-only Maximum 至少可在独立 Action 中达到双向各 **100Mbps 业务交付接近100Mbps**，但在 100Mbps 已遇 96块接收槽位上限的明确瓶颈。按照逐级容量规则立即停止更高档位；*不能*声称200Mbps已测或瓶颈实际发生在200。若未来继续性能优化，只在 FEC RX 有界维护处测算 active-time 与流速、最小扩槽；修复后重新构建精确 SOURCE，先原100Mbps反例及相关保护，再放行下一档，而不是直接盲加负载。W12原相同 VM AB 异常和 Auto 真动态另行未完成，`merge_ready=false`，未改网络岗位 status/main。


## 2026-10-24：用户授权继续350Mbps，但原生RX扩容后100Mbps业务复测未过

所有档位为每方向 UDP业务、99%1287B/1%64B、IID损伤30%、300ms单程、Maximum6、外层 DATA repair真正 OFF、15s warmup + **30s实测** +30s drain。各档位外层线路cap设为业务的4倍（100业务cap400），避免让线路速率天然卡死FEC冗余。用户要的「真实外层带宽，连重传都算」使用两个方向原始虚拟网卡 TX 字节差值 ×8/30s，包含首发、FEC parity、真实DATA重传及控制/反馈，不额外加任何子项。**这是网络namespace下 netem-veth interface TX 账本，不等于物理L1总字节，也不是分母45s的 native first_wire_bytes。** 数据已在各自 Action 的 `measurement_cpu.outer_tx_bytes/outer_tx_mbps` 和原生数值里。

| 来源 | 业务 Mbps/方向 | 业务交付 C→S/S→C Mbps | CPU-s 客户/服（30s） | RSS峰 MB 客/服 | 真实外层 TX C→S / S→C Mbps | 双向合计 Mbps | 原生 outer DATA repair | 判定 |
|---|---:|---|---|---|---|---:|---|---|
| [W13](https://github.com/lly8666/wbd-next/actions/runs/40090193642) RX96 | 50 | 49.985/49.990 | 12.54/12.67 | 29.72/29.57 | 87.006/86.884 | 173.890 | 0 | 单档PASS |
| [W14](https://github.com/lly8666/wbd-next/actions/runs/40091124249) RX96 | 75 | 74.967/74.979 | 16.79/16.93 | 34.44/35.10 | 130.329/130.180 | 260.509 | 0 | 单档PASS |
| [W15](https://github.com/lly8666/wbd-next/actions/runs/40094982877) RX96 | 100 | 99.956/99.968 | 19.40/19.54 | 39.69/39.92 | 173.655/173.827 | 347.482 | 0 | 业务PASS，96/96压力29425/端 |
| [W16](https://github.com/lly8666/wbd-next/actions/runs/40097487779) RX640 | **100** | **94.579/99.979** | **18.57/18.15** | **40.13/40.14** | **164.164/173.350** | **337.515** | **0** | **业务FAIL，RX压力=0** |
| 125、150、175、200、225、250、275、300、325、350 | — | **未测** | **未测** | **未测** | **未测** | — | — | W16 100业务失败，遵守 stop-on-first-failure |

W16真实 netem损伤29.984%/30.015%，业务C→S注入99.99863Mbps、交付94.57897Mbps、丢15993包；S→C注入100.00206、交付99.97866Mbps、丢129包。p99 303.1/303.2ms。FEC RX peak109/109 of640、bytes峰3.829/3.775MiB of48MiB，**pressure_evicted0/0、decoder_rejected0/0、reject_capacity0/0、reject_codec0/0**。真实FEC恢复到TUN client132655/server127783，源端TUN drop0、outer DATA重传0、native M4 source+parity非copy0，FEC parity rsent client554439/server554434，Stop drained。CPU PSI峰16.5%，没有CPU/内存高压抢占证据。W16产物 artifact `12561303555` SHA256 `0cc77ea7e6cc55bed5f1adacbd554bf90be64944b419996eadba2a92597e4d94`。

**分离不同时间窗的首发与重传真账本：** W16 native `V4_PUBLIC_M2_OUTER` 记原始首发账本（含 native 首次DATA/parity及相应record的独立 owner policy）client **1,376,830,446 B** / server **1,376,844,261 B**，覆盖 warmup+measurement **45秒**，平均 client244.770Mbps / server244.772Mbps；**实际 outer repair accepted=0B，uncertain=0B、retransmit copied=0**。这45秒首发 ledger不能与30秒 netem-veth接口 Mbps相加。外层网络 qdisc/netem记录约30%随机损伤，其中部分包被丢弃，真实送达接口TX数值不同；没有证据支持把整个差额称为物理线路限速、FEC codec错或CPU瓶颈。

**关键：** 与历史 W12 的同 VM 后段类似，W16在原生发送计数两侧接近（FEC rsent 554439/554434、原生 45s firstwire差不到14kB、双方注入均100Mbps）时，**客户端真实外层 egress 164.164Mbps，服务器173.350Mbps**，且接收服务器收到 source/parity 相应偏少。没有串行重传；旧 W15 单跑100Mbps双向通过，但新W16 100Mbps单跑出现显著非稳定性。已排除新RX slot压力，不可断言无证据的具体网络丢包根因。

**本轮收口条件：** 先修复或界定100Mbps可重复业务收支和 M4复制→netem接口送出差；不继续发125–350请求，不用刷种子掩盖回归。测试范围未涉及物理链路或任意重传ON，Auto动态和W12已知异常继续独立OPEN；`merge_ready=false`，没有更改上游network岗位。


## 2026-10-24：W19–W23 单向IPv4邻居根因及150Mbps首个性能拐点

**已确认根因范围：** W19 Action40100361068在 S2C 单向丢12.25%期间，服务端原生TUN依旧吞入约4900包/500ms、Rust M4 kernel copied持续，但服务端 veth/netem TX停止2.5-3秒，内核ARP peer NUD=INCOMPLETE探测4→6后REACHABLE时立即恢复；客户方向正常。内层wbntun0的原fq maxrate600Mbit flow_limit256仍启用、无TUN source/root fq drops。直接连接的实验veth对在root netem下让**ARP管理帧一起遭遇30%随机丢包**，因而使Linux邻居解析阻塞真实IP业务，即成功sendmmsg到netem接口之间的内核链路停顿。这是实验链路L2控制面的问题，不是 FEC source/Parity 计算失效或 fq600 的因果堵点。

最小修复提交87846904只改**测试专用** config/runner/合同：strict opt-in owned_veth_static_neighbour，默认false；仅在两个临时namespace安装彼此真实MAC的PERMANENT邻居，双向readback，不碰host sysctl、路由、生产产品、fq600或FEC数学；DATA和Parity依旧经过同样netem30%丢包与300ms延迟。W20 Action40101978371 500ms采样两端邻居PERMANENT各130/130、业务PASS；W21 Action40102339446关闭采样在原fq600下也双向PASS。原 W12/W16的类似出口中断仍保留旧失败数据，不直接断言所有实例都因ARP而失败。

| 原生Action | 业务Mbps/方向 | 真正交付C→S / S→C Mbps | 真实外层TX C→S/S→C Mbps | 总外层Mbps | CPU客户端/服务端 CPU-s (30s) | RSS峰客户端/服务端 MB | 残余/压力结果 |
|---|---:|---|---|---:|---|---|---|
| [W19 40100361068](https://github.com/lly8666/wbd-next/actions/runs/40100361068) 动态ARP | 100 | 99.965 / **87.746** | 173.311 / **152.439** | 325.750 | 18.22 / 19.28 | 39.71 / 39.88 | **FAIL: S2C NUD INCOMPLETE** |
| [W20 40101978371](https://github.com/lly8666/wbd-next/actions/runs/40101978371) 静态邻居+只读500ms诊断 | 100 | 99.969 / 99.985 | 173.549 / 173.523 | 347.072 | 19.79 / 19.62 | 40.40 / 39.93 | PASS，双端PERMANENT130/130 |
| [W21 40102339446](https://github.com/lly8666/wbd-next/actions/runs/40102339446) 诊断关闭 | 100 | 99.984 / 99.976 | 173.413 / 173.439 | 346.852 | 20.19 / 20.18 | 40.06 / 39.95 | PASS，RX pressure0 |
| [W22 40102622202](https://github.com/lly8666/wbd-next/actions/runs/40102622202) | 125 | 124.961 / 124.940 | 216.869 / 216.578 | 433.447 | 22.28 / 22.42 | 45.19 / 45.13 | PASS，CPU PSI>20占83% |
| [W23 40102994265](https://github.com/lly8666/wbd-next/actions/runs/40102994265) | **150** | **148.869 / 148.893** | **254.056 / 254.237** | **508.293** | **24.20 / 24.33** | **50.23 / 50.42** | 业务PASS**但性能拐点，停止加压** |

这些外层 TX Mbps来自各方向 netem-veth **30秒**接口真TX bytes差值×8/30，已经包含所有实际首发DATA、FEC parity、控制/反馈及任何重传（所有这些FEC-only样本真正original DATA retrans=0包/0B）；这是该层虚拟接口口径，不是物理L1线速。不能再加45秒native first_wire_bytes做总占用。

**为什么W23停止再上负载：** 150Mbps真实netem损失 client30.039/server29.958%，业务残余C2S0.754%、S2C0.738%（仍在1%门槛内但已无余量），p99 311.0/310.9ms，比125Mbps 306.1/305.8ms高约5ms。RX峰163/640、存储5.83/5.85MB<48MiB，解码拒绝及压力淘汰仍是0；TUN/root源端0丢包。但宿主CPU PSI峰**30.62%**，30秒样本超过20%占**100%**。FEC native计划的Parity行 client830246/server830265，M4确认rsent client800359/server799115，未发送缺口分别29887(3.60%)和31150(3.75%)，而125Mbps缺口client1358/692474≈0.196%、server1385/692502≈0.200%。150Mbps存在显著的期限内Parity调度/算力余量信号，原始原生 `unknown_capacity` client2983/server3054、`parity_seal`失败48/63需另案拆分；不能将计划差额等同于业务实际丢包，或用CPU PSI单独断言哪一个线程是根因。W23原始result artifact12563149315 digest f64b606746b3a7b317e81fb5fb8849447ceed1cc21607624508743567c01f9c4。

**停止条件：** 用户要求仅当未遇瓶颈才继续推向350；现于150出现Parity按时交付和宿主CPU调度压力，故175/200/225/250/275/300/325/350全部NOT_RUN（不是失败性能值）。后续若继续，先对 native TX parity deadline与各线程CPU/内核出口作窄域测量，保护优先发送原始DATA、真M4复制、有限内存及Stop；不要扩大队列导致延迟增大，也不要无证据调整产品fq600。Auto动态完整验收另行未完成，merge_ready=false；未合并main、未改原网络岗位状态。

## 2026-10-24 W24：150Mbps 旧/新同 VM 原生系数表复用 AB — 双腿未过容量门

独立 FEC 代码提交 [cf00a47c](https://github.com/lly8666/wbd-next/commit/cf00a47c9564d67b15409d50178a956416227a8a) 仅改动 `fec_v2.rs` native ISA-L 跨块不可变系数表缓存、单元等价测试及 ARM64 构建验证；静态槽位 `k∈[1,16]` × 20 × 4（最多 1,280），合法 native 表数据合计上限 777,600B，绝不缓存明文或 AEAD PN。源码没有增大队列或延长首次 DATA。新 SOURCE 构建 [40105262367](https://github.com/lly8666/wbd-next/actions/runs/40105262367) **SUCCESS** (产物12564910143，ZIP SHA256 `39809b55b380b4a161f47b367f734c2e45efa526efc36817e3ac6eb500c21d03`)，真实 ISA-L 跨块完整 Maximum 20 行与 oracle 对照2个PASS，固定及 Auto 的原 Go TLS→FEC→TUN 真实缺源恢复内核回归均 PASS；Maximum 原生行合同 [40105262390](https://github.com/lly8666/wbd-next/actions/runs/40105262390) PASS。

**性能 Action** [40105506052](https://github.com/lly8666/wbd-next/actions/runs/40105506052)，一次请求 `W24-maximum150-native-shared-tables-AB-arm64.json`，**同一 ARM64 runner 同一测量 job 顺序 A 再 B**，复用原冻结 A SOURCE `6b08527d` 构建40099179830和新 B SOURCE `cf00a47c` 构建40105262367；每腿 15秒预热＋30秒测量＋30秒排空，双向150Mbps，固定 Maximum6，30% IID 未固定种子但观测到 29.96–30.05%，300ms 单向，原始 owned TUN fq600、测试专有 veth 永久邻居、修复开关实际 OFF 和反向真实反馈保留。产物12564980324 SHA256 `cf2ba13a6a7876ba186f42fd424845bbc49b3a4c870137a3a10158204c581d98`，harness contracts [40105506150](https://github.com/lly8666/wbd-next/actions/runs/40105506150) PASS。

| 口径 | A旧源 | B系数缓存 |
|---|---:|---:|
| C→S 真交付 / 残余丢包 | 146.817Mbps / **2.153% FAIL** | 147.576Mbps / **1.642% FAIL** |
| S→C 真交付 / 残余丢包 | 146.376Mbps / **2.453% FAIL** | 147.302Mbps / **1.826% FAIL** |
| client Parity `rplanned / rsent` | 830151 / 749061 (9.77%缺口) | 830055 / 763348 (8.04%) |
| server Parity `rplanned / rsent` | 830134 / 737230 (11.19%) | 830127 / 754905 (9.06%) |
| client/server `queued expired` | 915 / 1102 | 817 / 882 |
| client/server `unknown_capacity` | 7679 / 8708 | 6295 / 7145 |
| client/server 30秒 CPU秒 | 23.91 / 24.46 | 23.98 / 24.32 |
| client/server RSS峰 MB | 50.57 / 50.36 | 49.39 / 49.71 |
| C→S、S→C p99 | 311.3/311.3ms | 311.2/311.2ms |
| 宿主 CPU PSI峰 / >20%样本占比 | 27.55% / 100% | 31.78% / 100% |
| 源TUN丢包、RX容量淘汰/codec拒绝、外层DATA重传 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

**判定：** 新 native ISA-L 表复用的 *功能* 合格，但改善幅度仅每方向约 0.76/0.93Mbps 与 parity 缺口1.73/2.13百分点，进程总 CPU 无显著下降；B 宿主 PSI峰更高。**A/B两腿均不能满足≤1%残余门限，禁止把旧 W23 单点 PASS 当作150Mbps可重复资格。** 原生45秒 Parity累计不可与30秒净业务包数混作相同分母。无 BA、未固定netem及共享主机容量拥塞限制因果判定；性能收益 *观察到趋势*，不能宣称严格归因。先定位10ms关闭后作业有效期内的逐量子 CPU/M4排队时间，不能仅因 `unknown_capacity` 字段名就增加接收缓存；在无新增原因前不再测175–350Mbps。自动档全动态阶跃/非对称与测量真实RTT年龄独立OPEN。**merge_ready=false**；不改原网络岗位的恢复算法及进度。


## 2026-10-24 W25：Parity 两个4行量子共用一次M4，150Mbps新源码限域通过

针对 W24 150Mbps 每侧失发 Parity 8–11% 和每秒910+个满块的 5 次 sendmmsg/结算，FEC-only 原生修复在一次 owner turn 先密封所有新 DATA，再只在空余≥8个M4 record槽时将**同一个** ParityJob 的两个≤4行原生M3量子一起密封，原生 M4 同一 syscall 按PN顺序归责；否则仍使用旧的≤4行单量子。代码 commit [aab45f7c](https://github.com/lly8666/wbd-next/commit/aab45f7cc304c09065e3614d0b5c61cff2097b56) + [ab7ea894](https://github.com/lly8666/wbd-next/commit/ab7ea894100f245d6a510137282736781bd017ce)（首个编译尝试原 Rust 二重可变借用失败，修复保留证据）；新精确SOURCE `ab7ea894100f245d6a510137282736781bd017ce` ARM64 build [40108972702](https://github.com/lly8666/wbd-next/actions/runs/40108972702) 成功，产物12565424535 ZIP SHA256 `9bf5b07eee3e90a37a69844b23fb08834c38a9d5781f0f1635c27543bbba7067`。包括 native staged prefix确证、不复发 PN、新 DATA 无阻塞、真实ISA-L和固定/Auto真正内核恢复回归 PASS；Maximum20 行合同40108972687 PASS。

[W25 Action40109234114](https://github.com/lly8666/wbd-next/actions/runs/40109234114) 同 VM **一个场景一个测量 job、A→B顺序**，旧A `cf00a47c`（构建40105262367）/新B `ab7ea894`（构建40108972702）均复用ARTIFACT，不在测量 job 编译。150Mbps **每方向**，原始fq600、Static owned veth邻居，30% IID实际netem 29.98–30.06%，单程300ms、最大档Fixed6 applied、外层真实DATA重传0包0B（parity另算），15秒warmup+30秒measure+30秒drain，双方Stop owned清理，源TUN/root drop0，RX pressure/decoder reject0。结果artifact12565917569 SHA256 `6dae0f82569e28a8c72785c126c1d18a3c6d322538a250b1f287d6f331705683`。

| 指标 | A旧源码（业务FAIL） | B双量子同M4（业务PASS） |
|---|---:|---:|
| C→S净业务/残余 |147.123 Mbps / **1.951%** | **149.938 Mbps / 0.0542%** |
| S→C净业务/残余 |147.379 Mbps / **1.774%** | **149.953 Mbps / 0.0485%** |
| 首次交付 p99 C2S/S2C |311.3/311.2ms | **303.3/303.2ms** |
| client parity rplanned→rsent |830066→745874（缺10.14%） | **830367→829702（缺0.080%）** |
| server parity rplanned→rsent |830066→753112（缺9.27%） | **830361→829936（缺0.051%）** |
| queued_expired jobs C/S |985 / 848 | **15 / 8** |
| unknown_capacity C/S |8049 / 7399 | **51 / 31** |
| 30秒进程CPU-s C/S |24.24 / 24.06 | **24.85 / 24.58**（无CPU节省声明） |
| RSS peak C/S MB |49.84 / 49.62 |50.12 / 49.78 |
| 30秒真实veth outer TX C/S Mbps |244.85 / 246.52 | **259.68 / 259.85**（包括更多真实Parity） |
| host CPU PSI peak |27.42% |29.61% |

**结论：** 新 B 150Mbps FEC-only 满足≤1%残余交付且 p99 相比 A低8ms；性能成果是 Parity按时发送与首次交付改善，**不是更低总CPU/总外层带宽**。B 发出了更多真实 Parity，故 CPU-s、外层 TX Mbps略升是合理成本，不能把少发 parity 的 A当作节能资格。整个 Action 按用户验收脚本判 *FAIL（A旧腿失败）*，但 B 腿原生产物 `PASS_SCOPED_OBSERVATION`；与W23孤立通过不同，本次是在旧版同机失败的情形下 B 正向通过，不过仍为一次未固定netem随机序列的AB而不是 BA/持续压测/物理保证。

**容量停止继续：** W25新B宿主CPU PSI峰29.61%、30秒持续高压力，175–350Mbps 继续 NOT_RUN；RX低占用、外层DATA retrans 0不代表宿主CPU可继续加压。Auto真实动态升降档、反馈RTT真实性以及 Windows 和整体合并仍未过；`merge_ready=false`，只改独立FEC分支与自身状态，不接管原network工作包。


## 2026-10-24 W26：取消每源包临时Vec及重复复制，150Mbps同机AB双腿PASS

在 W25 Fix Maximum6 150Mbps真实双向残余降到0.05%的基础上，本次只优化 FEC source 密封的CPU成本。旧 `original_fixed_stage_source` 每个源包先调用 `source_owned()` 创建新 Vec，再将同一 10B头+真实源字节复制到原 M1 arena，额外每侧约663,000次源包heap申请/45s。新精确SOURCE `564490bc7a8f61c9ab06be58add8138212306393` ([commit](https://github.com/lly8666/wbd-next/commit/564490bc7a8f61c9ab06be58add8138212306393)) 使用现有 `source_into` 对原 owned arena 精确 `[14..14+SOURCE_HEADER+len]` 写入，source/TICKET/budget校验、AEAD PN、复制确认、所有frame字节相同；不改 M3 Parity调度或外层恢复/真M2。Exact source ARM64 [构建40109847848](https://github.com/lly8666/wbd-next/actions/runs/40109847848) 全绿，zip artifact12566326717 SHA256 `a1ce0b81738a9a74ac04835546479ada398e99718fd5086775c0b765625f649c`，包括 dirty arena 源wire等价及 Fixed/Auto 内核缺源回归。

[W26 performance Action40110100061](https://github.com/lly8666/wbd-next/actions/runs/40110100061) **SUCCESS**：唯一场景、同一ARM64 runner/同一job、旧A `ab7ea894` →新B `564490bc` 顺序比较；各自warmup15s+measure30s+drain30s，双向150Mbps、真实netem IID约30%、300ms单程、固定最大6真正applied、外层DATA修复0包0B、真实首发Parity照常、原TUN fq600及owned测试静态邻居不动；Stop owned清理、TUN/source root丢包0、RX压力淘汰/codec reject0。结果artifact12565693815 SHA256 `d7127551bec2574ec38858e232cce03a65f3c76020c71856be9f389fb81e9051`。

| 同机30秒量纲 | A原双量子 | B+直接arena |
|---|---:|---:|
| C→S 实际交付/残余 |149.874Mbps / 0.1015%| **149.897Mbps / 0.0836%**|
| S→C 实际交付/残余 |149.871Mbps / 0.0954%| **149.926Mbps / 0.0623%**|
| 首次p99 C→S/S→C |304.5/304.0ms|303.7/303.8ms|
| CPU-s 客户/服务 |25.36 / 25.27 | **24.87 / 25.39**|
| CPU-s 双端合计 |50.63 | **50.26（少0.37s，-0.73%）**|
| RSS峰 客户/服务 MB |49.90 / 50.17 |49.85 / 49.71|
| native parity rplanned→rsent 客户 |830379→829009|830269→829411|
| native parity rplanned→rsent 服务 |830337→829059|830185→829614|
| 30秒outer veth TX 客户/服务 Mbps |259.71 / 259.49|259.85 / 259.81|
| Host CPU PSI峰/over20持续比 |30.58% / 100%|30.25% / 100%|

**资格**：W26 A/B两个方向、两腿各自产品级功能/业务均 PASS_SCOPED，B无Parity/首达回退；修订消除一次真实 source Vec 分配和重复copy。CPU 客户 -0.49s、服务 +0.12s，合计 -0.37s /30s，只有同机一次AB观测，**不能据此宣称有稳定0.73%硬件加速**。150Mbps比125Mbps多20%吞吐，CPU总秒不应硬压到125的绝对数而不减少真实Parity；更高175+依然 NOT_RUN，因为宿主CPU PSI持续>20%。独立 FEC Fixed 功能代表已具备150Mbps scoped资格；Auto真实损伤阶跃动态profile、真实反馈RTT age与Windows/组合资格仍未完成，merge_ready=false。现不再无限提高业务档或刷种子。


## 2026-10-25 W27/W28 用户要求：175Mbps与200Mbps原生双向逐档试验（外层DATA修复OFF）

产品冻结：Rust/Go 原生ARM64 W26 exact source `564490bc7a8f61c9ab06be58add8138212306393`，build Action40109847848 / artifact12566326717 / ZIP SHA256 `a1ce0b81738a9a74ac04835546479ada398e99718fd5086775c0b765625f649c`。两次性能Action均一个独立单腿场景（非同runner AB），依次先175后200；均为 ARM64 GitHub VM，Fixed Maximum6 真实双端applied，repair_enabled=false原生readback/实际outer DATA repair=0；原TUN fq600和owned静态veth邻居，150档延续的600Mbps外层netem rate不变，30% IID netem实测29.94–29.98%、单向300ms，15s warmup+30s measurement+30s drain，99%大小1287B，真实性能/PN/M2/RX和cleanup报告原样保留，不改代码不重新编译。速率仅改变 app offer `175/200` Mbps each。

| 双向重要指标 | W27 175Mbps | W28 200Mbps |
|---|---:|---:|
| 原生业务门 | **PASS_SCOPED_OBSERVATION** | **FAIL 2方向残余>1%** |
| C→S 交付 / 残余 |174.822 Mbps / **0.1187%**|191.462 Mbps / **4.302%**|
| S→C 交付 / 残余 |174.746 Mbps / **0.1661%**|190.519 Mbps / **4.765%**|
| C→S/S→C 实际首达 p99（仅已交付样本） |306.0/306.7ms|312.0/312.0ms|
| 客户端原生Parity rplanned→rsent |968003→965077（缺0.302%）|1106096→913794（缺**17.39%**）|
| 服务端原生Parity rplanned→rsent |967928→964020（缺0.404%）|1106095→893380（缺**19.23%**）|
| Parity队列过期Jobs C/S |69 / 96|**5864 / 6541**|
| 原生unknown_capacity C/S |116 / 172|**9320 / 10186**|
| 每侧进程CPU-s/30s C/S |27.11 / 27.53|28.64 / 29.08|
| host CPU PSI均值/峰值 |33.00% / 35.51%|**38.38% / 41.19%**|
| RX peak active C/S |183 / 183|209 / 210|
| RX capacity拒收/压力淘汰、原始TUN根fq/source drop |全部0|全部0|
| 真实外层DATA重传 / 假造反馈 |0 / 无|0 / 无|
| Stop原生命名空间清理 |PASS|PASS|

[W27 ARM64 Action40127642866](https://github.com/lly8666/wbd-next/actions/runs/40127642866) SUCCESS；请求 `tests/network/fec-work/W27-maximum175-W26single-static-owned-fq600-arm64.json` at `3a694dea12653eebe24bf5174f9c0c57e1cf533a`；result ZIP artifact **12573724068**, sha256 `00722004b9fbd1fc59e244b69045ff95ca0cdbe8ab008d4df1aa4bc9a5b0b7a0`。

[W28 ARM64 Action40127866107](https://github.com/lly8666/wbd-next/actions/runs/40127866107) FAILURE：仅两方向 `declared loss allowance exceeded`；请求 `tests/network/fec-work/W28-maximum200-W26single-static-owned-fq600-arm64.json` at `11774fb26d720f99f3c8801c5dfb843498f5dae8`；result ZIP artifact **12573539799**, sha256 `a5937ac9939a1d51c3693099b6a05163e09b2d5fbe9c8fe7c89efe0c4f7d9f53`。

**边界/解释**：175 Mbps业务单次限域达标，宿主CPU高争用不能保证多次/真实物理稳定；200 Mbps 双向残余显著超过1%，即使只看已交付的 p99 312ms貌似不高，也不能忽略50k+未交付。200Mbps对比175Mbps parity 未发比例突升至17–19%，作业到期数跃升，RX/源TUN均无压力拒收，因此首要调查发送端 Parity编码/调度在10ms期限下的CPU与M4排队，但单次共享runner不能全归产品CPU瓶颈。**容量STOP：不再压测225/250/350，不刷seed，不延长原生过期窗口，不降低loss资格要求**。Fixed-only 175有正例、200有确定反例；Auto真实升降档仍待独立资格，merge_ready=false，原network角色与main未动。

## 2026-10-25 W29：200Mbps两向PARITY发送时间堵点已修，CPU / SoftIRQ分核证据

**新 product 源码** [6246aa82](https://github.com/lly8666/wbd-next/commit/6246aa82df5140807914545b2fc9343b8c70a1aa)，ARM64 frozen build Action [40144596602](https://github.com/lly8666/wbd-next/actions/runs/40144596602) PASS，artifact **12579619244** ZIP SHA256 `f6baae3d9ca042d80b854fff1b217da8a11a2d8ce4aaf852935f2b641fdfcb7c`，Maximum20合同40144596591及真实Fixed/Auto原生FEC缺源恢复PASS，harness合同40144596705 PASS。区别旧 W26 `564490bc`：在原M4源包先密封后，严格以实际 32 个 kernel record槽位为上限，额外留 1 个反向真实M2反馈槽；有空位时最多一次聚合 5 个原M3 <=4行编码量子，0槽时只维护 owner deadline，不密封新Parity PN。每一行使用原owner唯一AEAD PN且仍等原生M4 definite-prefix确证；FEC r/k、T=10ms、源DATA优先、外层修复OFF、RX有界内存均不变。

[W29 同VM A→B Action40144809020](https://github.com/lly8666/wbd-next/actions/runs/40144809020)，一个200Mbps双向Fixed Maximum6相同网络场景，A=W26 frozen, B=W29 frozen，同一ARM64机器先后独立warmup15s、measure30s、drain30s，loss30% IID netem/oneway300ms/outer rate600Mbps/静态owned veth/FQ600，外层真实DATA重传两腿均0，真实TUN恢复、真M2反向反馈保留。结果artifact **12580009264**, ZIP SHA256 `786088a21a27c70623b344e2cfef5249c587005d2b103daf58a4a7b4600910a8`.

| 200Mbps each | A=W26 2个4行/原M4 | B=W29 最多5个4行/原M4 |
|---|---:|---:|
| 两向业务门 |FAIL/FAIL|**PASS/PASS**|
| C→S delivered / residual |191.527 Mbps / 4.271%|**199.546 Mbps / 0.2392%**|
| S→C delivered / residual |190.441 Mbps / 4.813%|**199.594 Mbps / 0.2201%**|
| 首达p99 C/S仅已交付样本|312.1/312.1ms|309.9/309.3ms|
| client Parity planned / sent |1106049 / 916875 (17.10%失发)|**1106174 / 1099275 (0.624%失发)**|
| server Parity planned / sent |1106089 / 899841 (18.65%失发)|**1106169 / 1099573 (0.596%失发)**|
| Parity queued expired client/server |5872 / 6537 |**330 / 310**|
| Parity sealer fail client/server |5949 / 5673 |**0 / 0**|
| unknown_capacity client/server |8701 / 9326 |**72 / 72**|
| CPU seconds /30s client/server |28.04 / 28.74 |30.61 / 30.38|
| CPU PSI mean / peak |37.78% / 40.84% |42.24% / 45.3%|
| CPU CPU time / 4 CPUs |74.5% nonidle |~76.9% nonidle|
| 软中断占整机CPU |10.05% |10.35%|
| 整核steal、hard IRQ CPU、cgroup throttled_usec |0 / 0 / 0 |0 / 0 / 0|
| 源TUN掉包、RX压力淘汰/reject、外层DATA重传 |0 |0|
| Stop清理 |PASS|PASS|

**分核真实内核证明**：新增FEC-only每秒numeric-only `/proc/stat` 所有CPU、`/proc/softirqs` NET_RX NET_TX TIMER SCHED RCU、`/sys/fs/cgroup/cpu.stat`及两个产品PID下线程级CPU ticks；`/sys/fs/cgroup/cpu.max`在此VM为UNAVAILABLE，不能从此字段直接确认配额类型。B测量窗口四核非空闲比例 76.55/76.90/78.02/76.16%，软中断CPU比例10.54/9.95/10.85/10.10%；NET_RX事件四核448058/437217/477315/447350，NET_TX四核522217/510686/548083/519130，并未集中在一个满负载核。cgroup `nr_throttled=0`、`throttled_usec=0`整个真实测量窗口均无增长，steal=0（不能排除<1Hz瞬时突发或宿主底层隐藏争用）。两端产品名截断的两个 `wbd-original-m4*` 高CPU线程分别约10.6~13.7 CPU-s/30s，说明TX/RX真正消耗CPU，非RAM短缺。

**机理与结论**：200Mbps上一版被固定Parity10ms期限+3次M4结算限制，平均全核未满仍有毫秒级等待，导致送出的r不足；`unknown_capacity`是deadline/capacity-known非内存malloc错误，且pressure_jobs/sources=0、RX容量拒收0；新B通过在同一次真实M4最多提交20行，消除额外kernel结算和原来超槽Pariy的失败，把两向业务从4%+残余带到0.22–0.24%，这是**同机一次比较下的限域通过**，并非持久、物理网络、高于200Mbps的容量保证。宿主CPU PSI仍高而且B需要更多真实Parity及CPU，保持200以上capacity_stop、merge_ready=false，原network角色与main不改。Action整体FAIL是故意保留的A旧版失败，B真实`PASS_SCOPED_OBSERVATION`。

## W30 (2026-10-25): 220Mbps frozen ARM64, narrow single-run PASS

Native W29 SOURCE 6246aa82, build40144596602 artifact12579619244 reused; original fixed Maximum6, real outer DATA repair OFF, authentic reverse M2 preserved. One standalone ARM64 job Action40145722367 artifact12581285466 ZIP SHA256 c2acba0adf8de8ae3cb7599e69930ba4e2582df0e4677f34632612010abd0e35. Real 30%IID actual client30.032/server30.002%, 300ms one-way, outer rate600Mbps, original TUN fq600, own static neighbor, each app rate220Mbps, 15s warmup/30s measure/30s drain.

C2S delivered218.145889Mbps, residual0.850472%, p99=312.0ms, missing5504. S2C delivered217.874079Mbps, residual0.977346%, p99=312ms, missing6325. Overall PASS_SCOPED_OBSERVATION but 0.02265 percentage points S2C margin to <=1% loss gate; no repeatability guarantee.

Native parity planned/sent client1216607/1186004 gap2.516%; server1216680/1182083 gap2.844%. Jobs expired1398/1588; unknown_capacity396/427 but pressure_jobs/sources=0 and parity_seal=0. Original TUN and root fq no drops; RX peak236/234 of640, bytes~8.9MB/48MB, pressure eviction/codec/capacity rejects0; no outer DATA retrans; genuine FEC recovered TUN 284121/285276, Stop cleaned.

CPU 30s client32.0/server32.11s; host CPU PSI mean45.53%, peak48.47%, >20% all samples. Each core nonidle79.16/80.22/80.36/80.93%, softirq CPU10.16/10.37/10.24/10.97%, NET_RX/TX balanced, steal0, cgroup CPU throttles0. Full-run original native TX thread21.6 CPU-s vs RX16.6 CPU-s EACH, not a 30-second counter. This is scheduling/CPU headroom, not memory exhaustion or one saturated IRQ.

Code-specific next candidate: StagedParity::next_quantum makes 4 new parity Vec + a Vec of mutable row views on each <=4-row ISA-L quantum, up to5 quanta per k16/r20 full block; W30 each end60k+ full blocks. Reuse four bounded row output buffers per stream for identical math, no change to AEAD, PN, deadline, first-send or copied prefix. Test against frozen W29 once, same VM old/new AB 220Mbps, after native function regression. Do not escalate >220, merge_ready=false.

## W31 (2026-10-25): 220Mbps per-stream Parity scratch same-VM AB

Exact new source 3b16e79698d33ef49628dfa8f67a47550438ebbc native ARM64 build Action40146207152 PASS, artifact12580177860 ZIP SHA256 69c14dbc1f3a65040c7013844c02d6af036b4a238c6d78262f6edc65d891b30f. W31 reuses only four bounded plaintext Parity row Vec per FixedStream, eliminates one temporary Vec row views per quantum, zeroes on Stop; exact independent scalar full Maximum20 parity row comparison and real native Fixed/Auto TUN recovery PASS, original PN/M4 prefix untouched.

W31 sameVM sequential A(old frozen W29 6246aa82) then B(new3b16e796) Action40146429352 artifact12580747651 ZIP SHA256 cf2ec141c998ea3a0259be51c43e95f2971af3f56017d2e1a92e5e2d254eb667. Both request outer DATA repair OFF actually0; Fixed Maximum6 both applied, original fq600 test permanent neighbors, 30%IID/300ms one-way, rate220Mbps each, outer rate600Mbps, 15s warmup30s measure30s drain, source root/TUN drop0, native RX pressure/capacity rejects0, Stop full cleanup.

| Measure 30s each | A old (INCONCLUSIVE) | B new (PASS_SCOPED) |

|---|---:|---:|

| C2S delivered Mbps / residual |218.704 / 0.5991%|219.322 / 0.3226%|

| S2C delivered Mbps / residual |218.825 / 0.5467%|219.244 / 0.3526%|

| First p99 C2S/S2C ms |311.4/311.4|310.4/310.7|

| Source injector S2C send errors |2|0|

| Client parity planned / sent |1216620/1197346|1216772/1207605|

| Server parity planned / sent |1216630/1198153|1216724/1206714|

| Expired jobs client/server |889/864|424/463|

| CPU process client/server seconds |30.97/30.87|30.95/31.24|

| Host CPU PSI mean/peak pct |44.26/47.54|44.18/50.44|

Important: Entire W31 Action failure is A INCONCLUSIVE due 2 genuine injector errors (APP_SEND_ERRORS_OR_MTU_REJECTION), not B failure. A observed business residual values are descriptive only, not a strict A PASS. B both directions true PASS_SCOPED_OBSERVATION, parity sent ~0.75/0.82% deficit vs A 1.58/1.52%. CPU total increased 61.84->62.19 CPU-s, cannot claim net CPU saving; may reflect sending more parity, runner variance, unseeded netem and source A injector error. Host PSI peak B50.44%, so no rate above220 and no sustained qualification.

Next plausible bounded CPU work visible in original codec: PreparedBlock per-job table reference BTreeMap, per-quantum dynamically allocated src/dst slice views inside encode_prepared_into, and original authenticated M4 TX. Profile before replacing; no CPU overhead attribution without timing breakdown. Keep outer DATA retrans OFF, native Auto dynamic unfinished, merge_ready=false.

## W32 2026-10-25: user-authorized 250Mbps diagnostic FAIL

Action40147431966 one ARM64 native W31 frozen source3b16e796, true Fixed Maximum6 dual applied, outer DATA repair=0, authentic reverse feedback, netem 30%IID/oneway300ms, app250Mbps each, outer600Mbps, original fq600, owned static-neighbour veth, warmup15/measure30/drain30.

C2S injected249.986Mbps delivered243.173Mbps residual2.7395% p99 successful313.3ms missing20146; S2C injected249.901 delivered243.547 residual2.5504% p99 successful313.3ms missing18749. Real injector UDP send errors C2S39 and S2C245, mirrored kernel Udp.SndbufErrors39/245: strict both business FAIL and injector contamination separately, no exclusively FEC cause claimed.

Original native parity planned/sent client1382114/1263176 (8.605% unsent), server1381771/1263279 (8.575% unsent), queued expired jobs5610/5587; neither pressure_jobs/sources nor parity seal/m4 noncopy nor RX capacity eviction nor original source TUN drops. CPU process30s client32.20s server32.49s, host PSI avg47.19% peak50.66%, >20% all samples; four CPU nonidle80.4/82.87/77.93/83.05%, softirq CPU10.42/11.45/9.63/11.44%, no percore IRQ saturation or cgroup throttle. Real artifact12581258712 ZIP SHA256 2d14df2efc9231f84fda1d1727529093d2eda7f5ed5a4a233a3be56dfe21d03a.

Follow-up bounded FEC W33 source e99a4afff validated real ARM64 build40147815858 and native Maximum40147815849, eliminates two slice Vecs each <=4-row ISA-L quantum and five coefficient BTreeMap nodes per full block; only limited fixed table refs and input/output stack arrays, retains exactly same Cauchy/ISA-L, AES/PN, source-first, reverse feedback, outer repair-off, FEC TTL=10ms, original fq600. 250Mbps W34 A old /B new single sameVM action40148014701 in progress. Do not claim pass or CPU gain until result; no higher pressure or branch merge.

## W34 2026-10-25: true 250Mbps sameVM old/new both PASS, host CPU variance explains earlier W32 failure

W33 source e99a4afff3e9e55e3a11113ed30097e1789e86af (fix of compile-only E0502 failed source ac4d9b21), native ARM64 build Action40147815858 real Fixed/Auto missing-source to TUN PASS artifact12580544395 SHA256 e1ec27312a833e03762a4b9bc6201ff143867b65a6dba02ce17a12a8bb9221eb; Maximum native row contract40147815849 PASS. Codec still exact global ISA-L (k,row,count), instead of per-quantum two heap-allocated pointer Vecs and per-block five BTreeMap coefficient reference entries uses fixed MAX_K16/MAX_BATCH_ROWS4 borrowed stack arrays and bounded 80-slot coefficient pointer array per in-flight block. No different mathematical output or FEC policy/M4 settlement.

[W34 A/B Action40148014701](https://github.com/lly8666/wbd-next/actions/runs/40148014701) **SUCCESS** single 4CPU ARM64 VM sequential A=W31 source3b16e796/B=W33 sourcee99a4aff, exact 250Mbps each, 30%IID netem/300ms one-way, outer netem600Mbps, unchanged original fq600 and owned static neighbors, original outer DATA retransmission truly0, authentic M2, warmup15 measure30 drain30. Artifact12581460257 SHA256 b64b94cebf5aa465421ee89bb310071401623820b9ed021630097fb92b5b785c.

| Metric | A old W31 | B new W33 |

|---|---:|---:|

| C2S delivered / residual |249.950Mbps / 0.02869%|249.936Mbps / 0.03631%|

| S2C delivered / residual |249.947Mbps / 0.03100%|249.950Mbps / 0.03127%|

| first-arrival p99 C2S/S2C |301.9/301.9ms|301.9/301.9ms|

| Parity planned/sent client |1382007/1381992|1381912/1381912|

| Parity planned/sent server |1381927/1381927|1381924/1381924|

| native parity jobs expired client/server |1/0|0/0|

| injector UDP send errors C2S/S2C |0/0|0/0|

| process CPU seconds/30 client/server |27.76/27.86|27.73/27.68|

| host CPU PSI mean/peak |33.66% / 36.11%|33.48% / 35.90%|

Both A/B true business/FEC-only scoped PASS and all native Fixed applied/zero source TUN and original root qdisc drops/zero RX pressure and codec reject, real recovered-to-TUN and Stop cleaned. **No causal W33 throughput gain:** observed combined CPU -0.21 seconds over30 (-0.38%); both parity complete and very similar p99/delivery; residual slightly higher B C2S. One AB cannot prove stable CPU saving.

**Cross-VM counterexample:** W32 on other shared Actions host, exactly same W31 old source3b16e796 at same250Mbps 30%/300ms, FAIL residual2.740/2.550%, real injector SndbufErrors39/245, native parity deficit8.61/8.57% and expired5610/5587; mean/peak CPU PSI47.19/50.66 versus W34 old A33.66/36.11. Host scheduling contention/CPU headroom and injector capacity are proven major sensitivities, no single-core IRQ saturation or cgroup throttling; cannot declare stable product250Mbps under high CPU pressure. Stop >250, no claimed host-fixed capacity, merge_ready=false. Further work should measure original TX M4 slot scheduling and high-PSI deadline age rather than chase ISA-L tables or enlarge RX buffers.

## W35–W38 2026-10-25: task-deadline-before-TUN / source symbol workspace / first packet-realistic 200Mbps A/B

Suggestion 1 verified: original TX worker called blocking poll(TUN,10ms) before checking owner 10ms post-close Parity and authentic M2 feedback deadlines. W35 source e2aeba7a fixed by computing nearest deadline before poll, waiting at most floor(time-to-deadline_ms) ≤10ms and zero if queued/already due; rechecks after poll. No new busy thread, M4 kernel proof/AEAD unchanged. ARM64 native PASS.

Suggestion 2 verified: each k16 FEC block used k separate Vec math symbols, despite already shared parity scratch and ISA-L tables. W36 source 861f0396 uses one contiguous zero-tailed k*symbol_len source workspace, reuses it across blocks only after synchronous true M4 copied-prefix settlement, scrubs on Stop, keeps Scalar/ISA-L math exact and first send unchanged. Corrected deterministic test expected 16*137B for mixed first-source135B plus15*77B block; native Fixed/Auto true TUN and Maximum20 PASS Action40150749260, artifact12582379708 ZIP SHA2565f9f587a4d1d44a3cf482c4c46a5be5b52cc71fdb4080935de153dc85f89f7e5.

Suggestion 3 examined: split ingress already exists for Normal/off using bounded channel512; Fixed/Auto intentionally keep one reader/TX. Under high host PSI do NOT add reader/thread without phase latency evidence; measured W38 shows product CPU and source TUN drops, so separate thread is not justified yet.

W38 same-VM real 200Mbps each, 96% UDP/4% two TCP socket, 35% count size64–256B and larger 512/900/1287B, 20Hz sparse64B probes,30%IID/300ms one-way, original outer600Mbps,fq600; first-arrival small actual application UDP cohort p99 and 10ms 300ms-delay-aligned gap, 15s warmup30s measured30s drain, real source zero-drop required, original outer DATA retransmission zero, authenticated M2. Action40150988880 FAIL both A/B, artifact12583045399 sha256 c90496f5f074082ac174de109d1830b3289f3f24d83ea61678e1df67d9cadb26.

| Metric | A W33 e99a4aff | B W36 861f0396 |

|---|---:|---:|

| C2S UDP residual |13.3746%|5.5686%|

| S2C UDP residual |13.7190%|6.3371%|

| C2S real small UDP<=256B residual / p99 |13.6155% /316.2ms|5.4765% /320.5ms|

| S2C real small UDP<=256B residual / p99 |14.0161% /316.2ms|6.3845% /321.3ms|

| TCP 8Mbps target each dir actual C2S/S2C |0.132/0.102Mbps|0.386/0.238Mbps|

| Client/server FEC jobs expired |40824/42260|14479/16998|

| Client/server Parity rplanned→rsent |1935490→1075756 /1932987→1042770|1926712→1628512 /1928128→1577641|

| Host CPU PSI mean/peak |43.48%/46.31%|56.57%/60.32%|

| Source TUN drops steady client/server |296/0|390/1017|

All outer DATA reTX0, RX decoder reject0 and RX capacity/pressure eviction0, exact native sender/rx recovered real TUN and Stop cleanup. CPU measurement in host process full-run (includes warmup/drain), not mislabelled 30s. Source drops and TCP backpressure explicitly disqualify. More FEC sent in B also raises CPU PSI, so don't claim stable CPU efficiency or full 200Mbps mixed capability. Lower effective app-byte target still increases packets/s enough to overload four-core runner. B improves parity deadlines but insufficient, do not extrapolate 250Mbps mostly1287B tests.

Size count distribution is illustrative workload (6/8/10/11/15/20/30 per 64/96/160/256/512/900/1287B), NOT externally trace validated representative Internet distribution. A 20Hz 64B distinct probe provides sparse small signal; W39 will provide true one-way first-arrival and loss distinct from RTT, at SAFE 100Mbps lower diagnostic after the W38 200Mbps capacity stop.

Status capacity_stop true, merge_ready false. No main or upstream network branch touched.

## W39 2026-10-25: 100Mbps same mixed packet distribution safe diagnostic with real sparse 64B first-arrival

After W38 mixed200 A/B both failed with source TUN drops/CPU PSI peak60% and TCP heavy backpressure, W39 intentionally de-escalates to single low-load 100Mbps each so it does not re-stress the capacity_stop host. This is not an attempt to replace or erase user's 200Mbps requirement.

Exact native W36 product source861f0396264734f97658243156060f13e6a2f74f build Action40150749260 artifact12582379708; original true Fixed Maximum6, outer DATA retrans OFF with genuine0, real M2 reverse, 30%IID netem actual,300ms one-way, outer600Mbps, source fq600, static owned veth, 15s warmup30s measure30s drain. Packet weights by count 64:6 96:8 160:10 256:11 512:15 900:20 1287:30 (35% <=256B). UDP96%=96Mbps, two actual Linux TCP socket flows share4%=4Mbps, separate20Hz64B probes.

[W39 action40151444036](https://github.com/lly8666/wbd-next/actions/runs/40151444036) SUCCESS true PASS_SCOPED_OBSERVATION, artifact12582309090 zipSHA256 80fa6550e58c62bdd884d22c816cf7a2f1ec6c5bd45fbe133d5f7723f62f80e0.

| Original business metric | C2S | S2C |

|---|---:|---:|

| UDP delivered / residual |95.958Mbps /0.0464%|95.978Mbps /0.0309%|

| 64–256B UDP sent / delivered |180355 /180240|180355 /180236|

| small UDP residual / p99 |0.06376% /308.6ms|0.06598% /308.7ms|

| netem-aligned longest offered small UDP 10ms zero-delivery gap |0ms|0ms|

| TCP 4Mbps offered / actual |3.9997Mbps, backpressure0|3.9998Mbps, backpressure0|

| TCP framed-record first arrival p99 |943.3ms|925.9ms|

| 64B 20Hz sparse probes sent/peer-real-first-arrivals |595/593|595/593|

| sparse probe one-way p99 / separate reverse RTT p99 |307.1ms /610ms|306.7ms /610ms|

| native Parity planned→sent / expiry |client1019107→1019107 /0|server1020072→1020072 /0|

Both source TUN warmup+steady drops=0, original fq root drops=0, RX capacity rejects0, outer DATA reTX0, Stop drained. Host CPU PSI mean37.65/peak40.43% still high; shared VM cannot establish physical/Windows capacity. Sparse probe first-arrival records receipt before reverse echo and is not inferred from the RTT; 2/595 real missing each side explicitly retained.

**Interpretation:** 100Mbps genuine mixed UDP+TCP and 64B sparse does recover correctly; previously W38 at200Mbps with same packet weights FAIL even though older mostly1287B250Mbps benchmark passed. Small packet count/second and kernel TUN throughput /20-row Parity encode scheduling (not a fundamental 64B header or decoder defect) are primary next questions. 200Mbps mixed is NOT qualified. Do not rerun overloaded 200 or increase rates without CPU headroom. Keep capacity_stop=true merge_ready=false.

## 2026-10-25 W40–W42: exact Linux nanosecond TUN/FEC wait and source-first bounded M4 fairness; AB/BA genuine 100Mbps mixed evidence

**Verified bug:** W35 original_fec_tun_wait_ms rounded future FEC/M2 due within 1ms down to `poll(fd,0)`. Linux poll(2) immediately returns when timeout=0, so idle sessions might spin until the deadline. W40 source 23da99f0de04afe17756542f5176f2759e318747 replaces it with Linux `ppoll` exact bounded nanosecond timespec, still waking immediately for genuinely ready TUN or due owner and never holding locks across sleep. Existing Normal/off/non-FEC 10ms behavior preserved. Unit asserts future900us creates real900us wait, future4.5ms creates4.5ms, queued/overdue=0.

**First simple scheduler not arbitrary QoS:** original Fixed/Auto original TUN/M4 32-record source-first batch. Read budget is 31 new DATA when no queued/near due FEC, preserving one genuine authenticated M2 opportunity. When queued Parity or native FEC deadline <=1ms, read at most23 new DATA, reserving up to 8 Parity rows across two unchanged <=4 ISA-L quanta plus one actual M2 entry. DATA remains 23/32 minimum, all source/TCP order and identical AEAD/PN remain, no new packet allocations/threads/scans, no modification to math/r or original DATA retransmission (still true OFF). On idle non-FEC nothing gets priority; no indiscriminate small/TCP tail reordering or application DPI. This is per-turn opportunity, not a guarantee of 200Mbps capacity.

**ARM64 correctness:** W40 native build [40153525640](https://github.com/lly8666/wbd-next/actions/runs/40153525640) SUCCESS Fixed/Auto original authenticated missing-source recovery to TUN, original M4 staged two quantum prefix, codec ISA-L native cross-block and Max20 row contract [40153525653](https://github.com/lly8666/wbd-next/actions/runs/40153525653) PASS. Artifact12583149711 ZIP sha256 d297411d00a312aeac2557fab6af21d70de88d13ac8a96244f8430081a227ff2.

**Both ordering controls pass** original 100Mbps each real 96Mbps UDP + 4Mbps true TCP two sockets, count 35% UDP application payloads <=256B among 64/96/160/256/512/900/1287B, separate 20Hz 64B sparse peers, one-way300ms /30%IID, original outer600Mbps fq600, FEC Fixed Maximum applied, outer DATA repair true OFF, 15s warmup30s measure30s drain. [W41 A->B Action40153771977](https://github.com/lly8666/wbd-next/actions/runs/40153771977) SUCCESS artifact12584120637 sha256 17e4fd8dfe1c872ed6ca6ecdc7ba84207ff4c2c4eff5a15f785c72442b5ea459; [W42 B->A Action40154125275](https://github.com/lly8666/wbd-next/actions/runs/40154125275) SUCCESS artifact12583383213 sha256 89a4b0014e590b0a66d8492efd817efe354909f875121a54e425065f94b2fa49. Both legs in each same VM, order reversed independent fresh runner to rule out always faster second leg.

| 100Mbps real mixed | W41 old A | W41 new B | W42 new B FIRST | W42 old A LAST |

|---|---:|---:|---:|---:|

| C2S true UDP residual% |0.04269|0.03338|0.02891|0.02950|

| S2C true UDP residual% |0.04463|0.03435|0.04657|0.03842|

| C2S small <=256B residual% |0.07707|0.05434|0.05600|0.05101|

| S2C small <=256B residual% |0.06820|0.05378|0.05877|0.06210|

| C2S small first p99 ms |308.7|307.7|307.7|308.2|

| S2C small first p99 ms |308.7|307.8|307.7|308.3|

| True CPU-s combined client+server, source analyzer `measurement_cost` |61.44|48.42|47.97|61.20|

| Host CPU PSI mean % |37.93|29.36|29.10|36.69|

| Sparse 64B 20Hz C2S missing |1/596|0/597|1/596|0/596|

| Sparse 64B 20Hz S2C missing |3/595|0/596|2/596|2/596|

| Native Parity copied vs planned |exact/equal both directions|exact/equal both directions|exact/equal both directions|exact/equal both directions|

| All Original Source TUN drops and test-owned root qdisc drops |0|0|0|0|

Real per-direction TCP application rate ~4Mbps all legs, no TCP backpressure, no outer DATA retransmission, native parity expiry0, authentic M2 and Stop cleanup. W41 CPU observation B -13.02s /61.44s = -21.19%, W42 inverse order B -13.23s /61.20s = -21.62%; stable in TWO independent A/B orderings, strong evidence the combined ppoll+bounded M4 change can lower CPU load in this 100Mbps mixed load. **Do not promise exactly 21% causal gain**: each leg also differs in CPU PSI on shared 4core Actions host (~8 percentage points), not controlled CPU core quotas or fixed physical host occupancy; nor is the contribution of ppoll vs parity reserve separately isolated. Small C2S W42 A happened to lose slightly less than B, so no unconditional improvement claim.

**Limit**: W38 200Mbps mixed on same underlying older W36 source A/B both FAIL 1% and source TUN drops + TCP injected <0.4/8Mbps under PSI mean 56.6%, not rerun high-load W40 and NOT qualified 200Mbps. This low-load result supports bounded scheduler and stops chasing trivial heap allocations; before a real congestion/QoS classifier profile original TUN read stalls, per-class original M4 actual bytes/age/feedback and ISA-L stages, then evaluate 200Mbps only on demonstrably sufficient CPU headroom. Do NOT reorder inner same-flow TCP payloads or add an extra thread by assumption. `capacity_stop=true`, `merge_ready=false`, main/upstream network branch untouched.

## W43–W47 2026-10-25: bounded performance finish; nonmaximum/normal/auto real native ARM64 regression

Exact frozen public ARM64 candidate product SOURCE `23da99f0de04afe17756542f5176f2759e318747` build Action40153525640 artifact12583149711 sha256 `d297411d00a312aeac2557fab6af21d70de88d13ac8a96244f8430081a227ff2`. No source changes after W40. GitHub harness requires one FEC request changed per commit: initial `063b9eda` grouped three requests and auto test selector failed BEFORE measurement; each W43/44/45 was re-committed separately (`b1fd495`, `b03a87c`, `1dc3171`) and all actual resulting Actions succeeded. No test failures hidden. Original fq600, authentic real packet TUN, no fake M2 or outer DATA repair; all caps low-load due W38 capacity_stop.

| Test and independent Action | Target and actual gate | Observed native/product result |

|---|---|---|

| [W43 FEC OFF normal 2Mbps](https://github.com/lly8666/wbd-next/actions/runs/40156880680) | 0% loss/25ms; count35% small/real TCP + 64B sparse | PASS, UDP/TCP fully delivered both, small loss0 p99 25.4/25.3ms, 597/597 true sparse each, source/root drops0, process CPU 1.27/1.29s |

| [W44 Fixed3 8Mbps](https://github.com/lly8666/wbd-next/actions/runs/40156902370) | 2% IID/75ms both | PASS, real two-end Fixed3 applied, small loss0 p99 89.0/89.8ms, true recovered-to-TUN, source/root drops0, process CPU4.13/4.10s |

| [W45 Auto 8Mbps](https://github.com/lly8666/wbd-next/actions/runs/40156921978) | C2S 2->20->1%/75ms, S2C 0->1->0% | PASS scoped UDP, authentic VALUE/QUALITY/REVISION stages: C2S 5->4 (03:06:54 UTC pre_low), 4->6 (03:07:15 UTC asym_high20%), 6->5 (03:08:43 UTC recovery1%); S2C 5->4 (03:07:33 UTC when s2c only1%), final native readback client requested=applied4 profile5, server requested=applied2 profile4, both pending=false |

| [W46 Normal OFF 2Mbps sameVM AB](https://github.com/lly8666/wbd-next/actions/runs/40157334097) | old W36 source861f vs new W40 23da | Both PASS, combined real CPU time old7.46 vs new2.45s/30s (~-67.2% one comparison), all UDP/TCP delivered, sparse597/597 each, small loss0 and p99 both25.3ms, source/root0 |

| [W47 Fixed3 8Mbps sameVM BA](https://github.com/lly8666/wbd-next/actions/runs/40157346725) | new W40 first then old W36, 2%IID/75ms | Both PASS, process CPU combined old20.54 vs new7.93s/30s (~-61.4% one comparison), Fixed3 applied, parity planned=sent jobs expired0, zero source/root drops, small loss0 both. Small S2C p99 OLD85.0ms vs NEW89.1ms (+4.1ms one sample), not universally better latency |

All end-to-end product runs have strict Stop cleanup, outer DATA retransmission0, zero source TUN drops and two independent real TCP socket streams to declared low rates. These are **scoped** checks, not universal low-load CPU reduction: shared host CPU PSI changed and tests not repeated per mode many times. W41/W42 two-order 100Mbps mixed previously showed -21.2/-21.6% CPU time and preserved small UDP business.

**W45 Auto auth detail:** `A/impairment-events.json` wall-time UTC pre_low03:06:25.456, asym_high03:06:55.456, recover_low03:07:55.456. `A/client-auto-quality.log` ORIGINAL Go native controller emits C2S 03:06:54 requested2 profile4 reason VALID 10s+4096 one step down; 03:07:15 requested3 profile6 reason VALID two rising fast windows; 03:08:43 requested4 profile5 reason VALID one step down. Server emits 03:07:33 requested2 profile4; independent s2c loss only1% in asym_high. Native final readback client auto requested4 applied4 profile5 pending=false, server auto requested2 applied2 profile4 pending=false; real native parity client155998/155998, server121187/121187, expired0, recovered original TUN client527/server11106, source drop0 and outer retrans0. High loss C2S has 47 missing out of 47066 app records, **0.09986%**, not 0.059% (corrects earlier conversational arithmetic). Automated summary `auto_runtime_curve='NOT_OBSERVED_FINAL_READBACK_ONLY'` does not claim automatic time-series verification: independently retained logs and actual netem time plus final applied readback support this narrow observation.

**Finite close decision:** Retain W40 Linux nanosecond ppoll and bounded per-turn M4 source-first cap31/23 with 8 Parity and 1 authentic feedback position when due. No small-packet DPI, flow reordering, extra threads or arbitrary priority hierarchy. Maximum full group k16/r20 needs20/16=1.25 parity rows per DATA source; 23DATA+8Parity per saturated turn cannot serve a permanent 1.25 demand and MUST NOT be called sustainable high-load proof. W38 200Mbps mixed W36 failed real host/TUN drops and severe TCP backpressure; current W40 still **NOT_RUN** at mixed200 and neither passed nor failed that target. capacity_stop=true; stop additional performance work unless real product user experience and sufficient CPU headroom identify a high-load cause. Not physical Linux/Windows or Auto aggressive whole matrix; merge_ready=false, main/upstream network branch never touched.

## W48–W50 (2026-10-25): real bidirectional 100Mbps mixed packet 10%→30%→10% loss step

**Contract**: user chose two fixed profiles (Maximum6 and a plausible 10%-capable low/mid) under real ARM64 original Go TLS/Rust TUN path, frozen W40 source23da99f0 build40153525640, outer DATA repair OFF readback with actual0, authentic M2, owned source TUN fq600, outer netem600Mbps each, 300ms each way. 10%IID 30s, 30%IID 60s, 10%IID 30s, plus15s warmup30s drain. Real app **100Mbps each direction**: UDP96Mbps (by packet count 35% 64–256B and remaining512/900/1287B), 2 actual TCP sockets share4Mbps, 20Hz separate64B sparsely paced UDP direct first arrivals. No adjusted netem/cpu/outer rate, no producer packet fabrication. Real kernels confirmed loss ~10/30/10% phase-by-phase. **This is a drop-rate step on independent packets, not temporally correlated Gilbert–Elliott burst/blackhole.**

To make distinct criteria testable, opt-in FEC-owned `acceptance.loss_gate_phases` with strictly validated phase names scopes UDP total+<=256B residual <=1% to the two10% phases for Medium/Balanced; it does not suppress high30 real loss data, per-phase genuine TCP injection/backpressure and errors, source TUN zero-drops, original root fq zero-drops, p99 gates, real Stop and Parity. Maximum leaves field omitted => all three phases strictly <=1%. Tests validated by network harness contract Actions; no product source changed.

| Profile / original Action | Initial 10% (30s) | Sustained 30% (60s) | Post 10% (30s) | Strict qualification |

|---|---|---|---|---|

| [W48 Maximum6 Action40158682220](https://github.com/lly8666/wbd-next/actions/runs/40158682220) | UDP missing C/S0/0%, small0/0%, real TCP4/4Mbps, small p99 307.4ms | UDP0.0388/0.0380%; small0.07845/0.06958%; TCP4/4Mbps, small p99 307.7ms | UDP0/0%, small0/0%; TCP4/4Mbps, small p99307.2/307.3ms | **PASS_SCOPED_OBSERVATION** all3 stages |

| [W49 Medium2 Action40158700155](https://github.com/lly8666/wbd-next/actions/runs/40158700155) | UDP0.149/0.162%, small0.187/0.215%; TCP3.73/3.68Mbps (already below4) | UDP18.95/19.11%, small18.60/18.99% knowingly ungated; TCP collapses0.45/0.43Mbps with backpressure | UDP0.165/0.150%, small0.223/0.175%; TCP only2.74/2.87Mbps, still backpressured | **INCONCLUSIVE** (Action failure from real TCP_BACKPRESSURED), no full 30s recovery |

| [W50 Balanced3 Action40159048877](https://github.com/lly8666/wbd-next/actions/runs/40159048877) | UDP0.0202/0.0105%, small0.0344/0.0183%, TCP4/4Mbps | UDP11.46/11.39%, small11.53/11.52% knowingly ungated; TCP0.76/0.84Mbps with backpressure | UDP0.0202/0.0180%, small0.0421/0.0233%; TCP only2.96/2.89Mbps, still backpressured | **INCONCLUSIVE** (Action failure from real TCP_BACKPRESSURED), not fully recovered |

Actual native original FEC Parity copied==planned and owner jobs expired0/unknown0 in **all profiles**: Maximum client3066375 server3060133; Medium client893598 server893843; Balanced client1197087 server1198724. Native rx capacity/pressure rejects0, original source TUN drops0, original root fq drops0, outer DATA retransmitted0, Stop original namespaces absent. Real independent 64B20Hz sparse probes and 10ms small-only TX/RX cohort continued at all stages; few missing on Maximum high, much higher miss proportional to unfixed 30% loss on Medium/Balanced; survivor first p99 small about306–308ms but does not disguise high missing. Inner TCP p99 Maximum high ~886/868ms returns to~306ms; Medium/Balanced high TCP p99 is unqualified/sparse (missing per-class latency sample) and recovered TCP p99 remains seconds (Medium~3964/7052ms; Balanced~3972/1923ms).

**Resource recovery by within-run phase-boundary genuine process CPU counter** (two original endpoints combined, 30s normalized; phase snap time is observed and phase switching may differ ~0.1s): Maximum 51.49 →47.82 →51.47 CPU-s; Medium37.92→32.29→37.51; Balanced39.65→34.95→39.26. Product CPU per actually delivered GiB last/first Maximum1.003, Medium1.001, Balanced1.004; no post-burst CPU inflation. Kernel netem end qlen client/server pre/post Maximum11197/11020→11169/10079, Medium6618/6454→6659/6124, Balanced7359/7378→7467/6775: no runaway **outer qdisc** backlog; this does NOT erase TCP sender backlog, which shows real backpressure and rate-collapse and persists post recovery for two lower grades. CPU PSI varies by **independent Actions VM** and raw CPU between different grades is not a sameVM efficiency comparison.

**Decision**: Maximum6 qualifies user-defined stepped-IID high-loss and post 30s throughput/CPU restoration at100Mbps mixed; Medium2 and Balanced3 pass only declared 10%-loss UDP/small gates and recover CPU, **fail requirement that real inner TCP service maintain/restore within30s**. High loss for lower grades is explicitly allowed to fail 1% packet residual, but not allowed to have dishonest TCP pacing claims. The causal source of long TCP recovery may involve original inner TCP retransmission/congestion window over 600ms RTT with residual losses; no evidence for FEC queue starvation, native parity deadline loss, or host qdisc overload. Do NOT interpret this as math kernel defect or claim Automatic profile-selection burst switching proven. Stop finite perf architecture changes; keep capacity_stop=true and merge_ready=false. Reproduce real user-facing issues/true correlated burst loss only if explicitly scoped.

## W51 2026-10-25 — Resume ORIGINAL FEC functional mainline from exact 3af257cd; genuine M2 positive confirmation latency

**User correction honored:** `experiment/fec-network-tuning` at exact `3af257cd1a353a47d424094a689fa5179b198a07` is the selected FEC functional mainline. W48–W50 special stepped-IID loss requests now CLOSED without rewriting or erasing their historical evidence. This W51 resumes that FEC branch, **no main branch merge/import, no network-matrix code, no change to native FEC math/priority/Rust packet engine or outer DATA restoration**.

Original Rust already exposes native full cumulative 8s-mature `positive_confirmation_lag_ns` and `positive_confirmation_samples` for actual original M4 first-copied DATA with unambiguous original M3 authenticated reverse kind1 M2 positive. Go Auto already consumes the same `rustOwnerFec2MatureQuality` array. W51 narrowly publishes `positive_lag_ns`, `positive_samples`, `positive_mean_us`, and `positive_mean_known` in original-Go CLI FEC M2 proof (client/server) through existing read-only bridge. No samples -> UNKNOWN, never fake 0ms or fallback `srtt_us=600000` (OFF outer shadow default); logs require actual original native proof. The reported latency measures first copied DATA to positive authenticated confirmation including feedback scheduling, **NOT one-way latency, TCP RTT, FEC age, or p99**. No new control/feedback packets, no per-packet Go work.

Exact new source [e446fa1cf09ebfb259da3d764abf8f8ed8d4211f](https://github.com/lly8666/wbd-next/commit/e446fa1cf09ebfb259da3d764abf8f8ed8d4211f); native ARM64 actual product [build40167423967](https://github.com/lly8666/wbd-next/actions/runs/40167423967) SUCCESS (original TLS, ISA-L native, M4 two quanta, deterministic missing source to TUN, Go Auto latency counter proven). Artifact12588789024 frozen SHA256 `3bac82b33642335ed3691c763d66c3c556c575f38f92fd635073fc9673ea1cb4`. New scoped network harness parser validates both native fields, arithmetic/false unknown, does NOT rewrite historical older artifacts; contracts [40167596889](https://github.com/lly8666/wbd-next/actions/runs/40167596889), [40167677632](https://github.com/lly8666/wbd-next/actions/runs/40167677632) SUCCESS.

True product [W51 Action40167733514](https://github.com/lly8666/wbd-next/actions/runs/40167733514) `PASS_SCOPED_OBSERVATION`, original 8Mbps each, Fixed3 (requested=applied1 both), 2%IID/75ms one-way, mixed UDP96% two real TCP sockets4%, small35% packet count, independent sparse64B20Hz, outer DATA repair0, owned TUN fq600, warmup15/measure30/drain15. Actual ZIP artifact12588149669 SHA256 `bec3f9384f16a52356a443aac2e4d30f60edd250bce0321a332596991dd25485`.

| Original native proof | Client | Server |
|---|---:|---:|
| 8s-mature original M2 positive DATA samples | 53,875 | 53,938 |
| Actual positive lag sum ns | 8,241,048,743,812 | 8,249,165,558,731 |
| Real positive confirmation mean us | **152,966** | **152,937** |
| Authentic reverse reports | 11,346 | 11,400 |
| 2s/8s uncovered UNKNOWN | 161/161 | 175/175 |
| First/coverage censored flags | 1/1 | 1/1 |
| Native parity planned/sent | 34,699/34,699 | 34,710/34,710 |
| Parity owner expired/capacity unknown | 0/0 | 0/0 |

Both actual 7.68Mbps UDP +0.32Mbps TCP each direction delivered with app record loss 0; small UDP loss0 first p99 C→S89.1ms S→C89.4ms; no original source TUN/root drops, no outer DATA retrans, original Stop cleanup success. **Native M2 censorship/UNKNOWN is retained and is NOT erased by these positive samples.** No claim that the entire 8s cohort is clean/valid or that this is standalone clock-based RTT. Actual FEC confirmation mean near 153ms is plausible for 150ms baseline RTT, not an inferred echo or shadow timing.

**Next FEC mainline:** confirm new exact source Auto asymmetric genuine authenticated stage and confirmation metric once, then finite original FEC product MTU boundary and Stop/generation as needed; no tier/peak throughput extension. Keep `capacity_stop=true`, `merge_ready=false` and do NOT merge into main or import its network recovery.

## W52 — same exact FEC MAINLINE Auto native M2 provenance, asymmetric stages, no false claim of C2S downshift

Frozen source e446fa1cf09ebfb259da3d764abf8f8ed8d4211f (a direct FEC-only descendant of user's selected 3af257cd). Standalone [W52 ARM64 original product Action40168045298](https://github.com/lly8666/wbd-next/actions/runs/40168045298) SUCCESS, artifact12589925435 SHA25622a5b1de99366e172d11fd3f9e47dabf70a47e874b18ec0e4e3152f373dbcf04. No new Go/Rust product source after W51; no import from main or other network branch; original outer DATA repair OFF and authentic M2 still same.

**Caution actual W52 workload**: W52 reuses original W45 Auto native product regression, **UDP only** at 8Mbps each, UDP size 64B1% +1287B99% by packet count, separate UDP probes20Hz, NO TCP mixed, not 100Mbps. True netem c2s 2%30s then20%60s then1%60s, s2c0/1/0%, one-way75ms each, genuine Go TLS owner and Rust original M4+M2, warmup15/drain30. All three phases UDP delivered ~8Mbps both directions. C2S high 20% original app missing0.014872%, all other directional phases missing0; client native parity planned/sent167271/167271, server121021/121021, expired0, source TUN drops warmup+steady0, outer DATA repaired0, Stop + owned netns clean.

**Native ORIGINAL M2**: client positive unambiguous samples118931 original native firstsend confirmation age mean153665us, reverse authenticated reports38413; server samples129400 mean154241us, reverse reports33050. M2 includes 2s UNKNOWN client3/server54 and first/coverage censored flags1, not magically globally clean; this is not shadow RTT (outer OFF srtt_us fallback600000 with timing_samples0), nor first-arrival p99.

**Independently verified Auto stages** from saved original `client-auto-quality.log`, `server-auto-quality.log` and netem wall clock:
- at06:09:52 UTC the c2s 20% phase began; **06:09:58** genuine VALID original stage C2S Strong(5)->Maximum(6), requested revision2; original final readback C2S requested2 applied2 profile6 pendingfalse.
- s2c stayed at1% during asymmetric high and dropped from Strong(5)->High(4) at **06:10:39** VALID, then when s2c loss0 during low stage, High(4)->Balanced(3) at **06:11:42** VALID; final requested3 applied3 profile3 pendingfalse.
- c2s low loss1% began **06:10:52**, held60s. **No C2S lower profile stage** in this run; final still Maximum6. This is a true scoped gap compared with earlier W45 source23da99 where C2S stepped down. Original conservative `FecV2Step` deliberately requires computed next-lower residual <=0.0005 before a 10s+4096-source downward move; and old logs show many UNKNOWN due missing feedback/actual-k windows. No evidence warrants making fake line-truth ACKs or forcing downgrade. W52 product all green means **application+auth rise/independent direction** pass; does NOT mean entire recover/down Auto curve proven. The prior W45 positive remains separate historical evidence and should not be erased or generalized.

Next mainline work must be surgical: evaluate exact saved W52 window quality and predicted next-lower threshold vs W45, then bounded MTU/Stop/generation tests if needed. **No merges, no main changes, no repeat performance ladder, no Game/Windows claims.**


## 2026-10-25 — W53–W60 native FEC-only closeout: user's per-grade Auto tolerance and common business coverage

**User's latest accepted Auto behavior supersedes the earlier tight full-curve request:** rapid authenticated UP (transition loss tolerated), one-profile-at-a-time gradual DOWN; **up to 2–3 minutes PER grade**, multiple grades' elapsed times may add, but sufficient stable low loss/valid evidence must eventually return from excess protection. No fake ACK/UNKNOWN-as-clean, no forcing profiles from netem truth, no new load/rate ladder. Native source/product used for common-case validation is [1673cd96](https://github.com/lly8666/wbd-next/commit/1673cd96caea6a5764ace1adbd5573da18e46c85), exact [ARM64 build Action40173359338](https://github.com/lly8666/wbd-next/actions/runs/40173359338) SUCCESS, artifact12590822815 ZIP SHA256 `cdc5d4eb68621321f7f918b6667ff16c0a166bfe6b509ded310afc467294a97f`. Its Go cold 2s Auto adjustment validates source-k histogram cohort overhang <=5% conservatively, still requires genuine original mature M2, >=5 VALID windows, >=4096 authentic sources, hold10s, and native applied revision. No outer recovery algorithm or default ON policy changed.

**Original Auto W56** [sameVM AB Action40173582990](https://github.com/lly8666/wbd-next/actions/runs/40173582990) SUCCESS, request SOURCE `9ec341e6`, artifact12591456771 SHA256 `1bc9dfade3a26016e5d80dd610da1801a6d6e291c1322aea9517b47e302487ce`: A prior `f3b9e8a5`, B `1673cd96`, same ARM64 VM sequential. 8Mbps UDP only each, C2S IID2%30s→20%60s→1%90s and independent S2C0/1/0%; 75ms one way; outer DATA repair truly OFF both. B genuine client sequence 5→4→3 before high, **3→Maximum6 UP under 20%**, then 6→5→4→3→2→1→Light0 during recovery, each VALID and truly requested/applied; server 5→4→3→2→1→0 independently. New B client quality 75 VALID/31 UNKNOWN vs A41 VALID/64 UNKNOWN; **not** all feedback clean. B 20% C2S main UDP missing62/47068 =0.1317% (rise loss accepted), 1%-recovery missing0, p99 ~79.1ms; genuine native parity/recovered-TUN and positive M2 both. CPU A17.42/17.63 versus B16.54/17.02s on same VM; different actual protection histories, cannot claim causal CPU optimization. Detailed receipt: `20261025-W56-authentic-k-source-native-Auto-sameVM-AB-PASS.json`. **Meets latest per-grade 2–3min criterion; no more Auto timing micro-tuning.**

**W57 finite native boundary** [Action40173816559](https://github.com/lly8666/wbd-next/actions/runs/40173816559) PASS on ARM64: FEC codec odd-length/MTU, recovered source+Stop, retired k1 parity, shared original MTU±1/generation/Stop and 65KiB two-turn segmentation/unit. Shared-path scopes are *not* actual 65KiB FEC-through-TUN product, Game or Windows qualification. Receipt `20261025-W57-bounded-arm64-FEC-MTU-generation-Stop-PASS.json`.

**New common scenarios** (one scenario per performance Action, each independent ARM64 VM; same frozen source and binary, no cross-VM CPU percentage claim, outer repair off, original TLS+TUN, true parity and authentication):

| Case | Original mixed business (8Mbps each, 96% UDP/4% two TCP flows, varied 64–1287B packets, 75ms one-way) | Main app UDP missing C2S/S2C | TCP, first-arrival, resource and native facts | Result |
|---|---|---|---|---|
| W58 Fixed **Medium2** IID5% 60s [Action40174383391](https://github.com/lly8666/wbd-next/actions/runs/40174383391) | Netem 50Mbps each, real partial k class+20Hz 64B probes | 5/82440, 4/82440 | TCP 0 missing both, native requested/applied1/1 both, parity planned=sent45183/45173, actual recovered TUN5665/5528, UDP p99 90.0/90.1ms; CPU8.11/8.05s, RSS22.6/22.7MB; source TUN0, owner Stop clean | **PASS_SCOPED** |
| W59 Fixed **Strong5** IID15% 60s [Action40174386036](https://github.com/lly8666/wbd-next/actions/runs/40174386036) | Same packet distribution, strong redundancy | 0/82440, 0/82441 | TCP0 missing both, native requested/applied1/1 both, parity111353/111351 full, recovered TUN16590/16685, UDP p99 91.5/91.5ms; CPU8.93/8.90s, RSS23.0/23.0MB; source TUN0, Stop clean | **PASS_SCOPED** |
| W60 **Auto 1%30s→5%60s→1%120s** [Action40174389833](https://github.com/lly8666/wbd-next/actions/runs/40174389833) | Same mixed traffic, symmetric normal fluctuation; initial Strong protects medium loss | C2S0/2/19 and S2C0/0/16 over three phases | TCP0 missing both; authentic per-direction 5→4→3→2→1→Light0, final requested=applied6/pendingfalse both; parity133411/133311 planned=sent, recovered TUN6876/6913, all recovery p99 76.5ms; CPU28.31/28.49s **for 210s measurement**, RSS22.9/23.6MB; source TUN0, Stop clean | **PASS_SCOPED** |

For W58/W59 independent sparse 64B probes, missing2/1191 and8/1190 (Medium), 6/1190 and5/1190 (Strong) even though main mixed stream is almost/fully delivered; no false absolute zero-loss claim. W60 1%-recovery also still misses main UDP19/164903 C2S and16/164904 S2C, while tiny TCP has no missing; do not report zero universal loss. All three Actions' native real outer DATA retransmission is **0**, FEC parity emitted separately, genuine reverse M2 positive mean ~153ms and native TUN recovery positive, no RX capacity pressure, host CPU PSI ~1%, stopped and owned cleaned. Exact receipt/ZIP hash in `20261025-W58-W59-common-real-mixed-arm64-PASS.json` and `20261025-W60-common-real-auto-mixed-arm64-PASS.json`; new harness contracts all SUCCESS.

**Scoped integration handoff:** The Linux ARM64 native FEC-only Normal/FEC-off, Fixed (representative mild-to-strong/maximum), Auto authentic fast-rise and gradual-down, original M2, parity-only recovery, first-TUN, CPU/RSS, source boundedness and finite MTU/Stop protection now have representative Actions receipts from exact sources. This is **ready for SCOPED integration review**, not blanket `merge_ready=true`: no full Windows/Game native public product qualification or actual 65KiB jumbo through FEC TUN; W49/W50 historical 100Mbps 10→30→10 mixed **inner TCP recovery remained backpressured**; W40 200Mbps mixed not run; independent VMs not CPU AB. Preserve high-rate capacity_stop and do not import or modify main/network-matrix code. At integration, review exact source/cherry-pick paths and common owner overlaps; any merged combination needs its own exact-SOURCE Actions. This report is for the isolated branch only, **not a merged PR or main release**.


## W61–W68 — Both client/server host CPU insufficiency: authentic Auto DOES NOT falsely raise under tested real TUN loss

**Question:** If client or server cannot process packets fast enough and the **host** drops them (not the external path), does original FEC Auto mistake this for remote line loss and increase redundancy? This is a new **scoped** host-overload investigation, not a repetition of the accepted link-IID rise/down or a merged product qualification. Exact unmodified original native ARM64 FEC product source \`1673cd96caea6a5764ace1adbd5573da18e46c85\`, existing build [40173359338](https://github.com/lly8666/wbd-next/actions/runs/40173359338), artifact12590822815 ZIP SHA256 \`cdc5d4eb68621321f7f918b6667ff16c0a166bfe6b509ded310afc467294a97f\`. No native Auto threshold, FEC source/parity or outer recovery source modified.

**Original FEC-owned test-only harness** commits \`d16a2617\` → \`c219fcc7\` → \`6321c302\` → \`36582b27\` → \`623ac5ce\`: a test-only phase-scoped, 0%-netem FEC Auto outer-off switch; pin **every** Go/Rust process TID (not Linux main thread only) to one available CPU and verify readback at both endpoints of stress; give it bounded 12 Python or 32 native \`yes\` same-core competitors while independent business generators remain free; in W67/W68 optionally pause the process with SIGSTOP for **exactly 7s** at +20s and resume with SIGCONT, with guarded restore on end/cleanup. Traffic 8Mbps *each* direction (UDP96%, two original TCP sockets4%, varied 64–1287B, sparse20Hz probes), one-way75ms, netem **loss0%** both, 30s control→60s host stress→90s recovery, 15s warmup/drain30. Each Action one scenario with exact same prebuilt binary. No fake ACK, injected FEC feedback, invented network loss or global host throttling.

| Case | Target and verified stimulus | Stress phase measured business UDP C→S / S→C missing | Auto stages and endpoint kernel source drops | Classification |
|---|---|---|---|---|
| W61 [40176086163](https://github.com/lly8666/wbd-next/actions/runs/40176086163), W62 [40176089227](https://github.com/lly8666/wbd-next/actions/runs/40176089227) | Target client / server, 12 Python workers **leader-only** affinity | Not full-process-valid | Did not confine Go/Rust worker TIDs: explicitly exploratory, NOT actual starvation qualification | exploratory only |
| W63 [40176341191](https://github.com/lly8666/wbd-next/actions/runs/40176341191), W64 [40176348148](https://github.com/lly8666/wbd-next/actions/runs/40176348148) | Client / server, **all 14** product TIDs, 12 competitors alive | **0 / 0 each run** | 0 source TUN drops, **0 UP**, authentic one-grade DOWN to Light0 both | \`PASS_SCOPED_OBSERVATION\` but NO host packet loss |
| W65 [40176790249](https://github.com/lly8666/wbd-next/actions/runs/40176790249), W66 [40176793874](https://github.com/lly8666/wbd-next/actions/runs/40176793874) | Client / server, **all 13** product TIDs, **32** native competitors alive | **0 / 0 each run** | 0 source TUN drops, **0 UP**, both converge to Light0 | \`PASS_SCOPED_OBSERVATION\` but NO host packet loss |
| W67 [40177265469](https://github.com/lly8666/wbd-next/actions/runs/40177265469) | Client **13/13 TIDs pinned**, 32 competitors, **7.00018s actual client SIGSTOP/CONT** | **9,113 / 9,140** | Actual **client source TUN TX kernel dropped 9,291**, server0; **0 UP**, 5 authentic DOWN per endpoint, requested/applied rev6 Light0 after recovery | **\`INCONCLUSIVE\`: actual host-upstream packet loss** |
| W68 [40177269298](https://github.com/lly8666/wbd-next/actions/runs/40177269298) | Server **13/13 TIDs pinned**, 32 competitors, **7.00015s actual server SIGSTOP/CONT** | **9,140 / 9,106** | Actual **server source TUN TX kernel dropped 9,286**, client0; **0 UP**, 5 authentic DOWN per endpoint, requested/applied rev6 Light0 after recovery | **\`INCONCLUSIVE\`: actual host-upstream packet loss** |

W67/W68 30s pre and 90s recovery **each** measured 0 missing main UDP either direction; stressed phase main TCP reported 0 packet missing but first arrival p99 rose to ~7s, recovering to ~76ms. Actual native M2 quality tracked both VALID and UNKNOWN, and the peer to the stalled endpoint saw up to 27/65 (W67) and 69/81 (W68) fast/slow genuinely observed missing counters. **Native \`HOST_CAPACITY\` did NOT appear**, so success in preventing false escalation here is not evidence that its host-capacity indicator detected remote overload. No grade-UP stage occurred on either directional controller; all five revisions down occurred from genuine VALID, NOT forced by netem truth. Both W67/W68 genuine native positive M2 receipts, native source/parity and final applied readback observed; original DATA retransmitted0, Stop drained and owned netns cleaned. W67 actual parity planned/sent client102974/102974, server106073/106073; W68 server102746 planned/102710 sent and 9 expiration during host pause, so do NOT claim all parity lossless.

**Action status distinction:** W67/W68 performance workflow conclusions are **failure** by the harness' correct upstream source TUN drop gate, while each saved \`A/result.json\` is \`INCONCLUSIVE\` with \`SOURCE_TUN_TX_DROPS: kernel upstream loss before product\`. Those are **positive proofs of real host-induced loss and no false Auto-UP under this finite stall**, not an overall business/service PASS. Zero netem injection and genuine app missing are separate facts. CPU contention alone (W63–W66) wasn't enough for real drop; 7s deliberate scheduler pause is an extreme bounded diagnostic, not evidence for all persistent overload patterns. A sender without an authenticated peer host-capacity signal cannot in general infer why externally identical missing packets vanished, and longer sustained host loss remains unqualified. **No Auto product code change**: the tested false-UP defect did not reproduce; changing model thresholds here would jeopardize W56 authentic rapid line-loss rise without causal proof. Local TUN ingress loss must instead be handled at host capacity/scheduling level; FEC cannot reconstruct source never staged. The existing scoped ARM64 integration review remains allowed, full merge-ready **false**, capacity-stop **true**, no main/network branch change. Exact files, artifacts, SHA256 and positive/negative caveats: \`docs/evidence/fec-network-work/20261025-W61-W68-CPU-starvation-host-loss-Auto-no-false-up.json\`.


## W69–W76 — Genuine own-product overload, bounded native Auto host-capacity recovery **SCOPED DELIVERED**

**User question refined:** not merely external CPU competitors or 7-second stopped product, but whether the original client/server **program's own high packet rate exhausts host resources**, causing local loss and then **spurious Auto FEC UP**, a costly overload spiral. True TLS-bound original Go/Rust Linux ARM64 product with independent sender/receiver and original M2 authenticated reverse receipts, FEC2 M1/M3/M4 parity+TUN first-delivery; the real original outer DATA repair is **OFF and 0 packets**. The overload network is strictly netem loss0% / 500Mbps cap / 75ms each direction, 96% UDP/4% two real TCP flows, 64B60% +256B30%+900B10% by count plus sparse probes. Every independent Action has one scenario; A/B sources are frozen artifacts and run sequentially on SAME ARM64 VM. Do not confuse 0%-**injected** loss with zero host drops.

- **W69** [Action40179143633](https://github.com/lly8666/wbd-next/actions/runs/40179143633) old frozen source1673cd96, 6→18→36→6Mbps per direction: no app main UDP missing, no source TUN drop; Auto DOWN to Light0, **PASS_SCOPED** but *no real overload*, so cannot answer the failure case. Artifact12593946020 sha256 947384b95c0a6bb253de06145d7ce3036a605925da9c74016d8ed36be80597ce.
- **W70** [Action40179596226](https://github.com/lly8666/wbd-next/actions/runs/40179596226), real 6→60→6Mbps/side: peak local source TUN TX drop **client774/server1153**, UDP C2S2466/S2C1923 missing, recovery0/0. 0 genuine Auto UP, **but the original Auto was stuck Strong5**: Go read lifetime cumulative native sender M2 \`capacity_censored\` raw[11] as an everlasting HOST_CAPACITY bit. Result \`INCONCLUSIVE\` under real source TUN upstream loss, not performance PASS. Artifact12593656927 sha256 d0bb36f52d342a9dfb40745c9b858b03dbb4bede68e6e9b591b5849e2b5363f3.
- **W71** [sameVM Action40180341171](https://github.com/lly8666/wbd-next/actions/runs/40180341171): Go authentic recent 16s capacity delta source\`ca56932a2\` allowed real VALID one-grade DOWN requested2 High4, but native \`applied1 pendingtrue\` indefinitely both. A lifetime-frozen original reference; B genuinely FAIL native apply. Artifact12593703755 sha25602465d7ce1471f102774fe6c548b4cc8363e78ee1ec661b0818ba33af2cf3464.
- **W72** [Action40180375088](https://github.com/lly8666/wbd-next/actions/runs/40180375088) Go fix / original native, true link IID C2S2→20→1%: authentic rapid UP Balanced3→Maximum6 and DOWN to Light0, PASS_SCOPED. Artifact12593843118 sha25693c78088614988e55eb546db5b66353753bece232a31b45a16019ad721e3b03e.
- **W73** [sameVM Action40183965888](https://github.com/lly8666/wbd-next/actions/runs/40183965888): original Rust FEC-only seamless cutover now closes old open source blocks under their old matrix, maintains monotonic shared block identity/old parity proof; actual High4 parity appears, but BOTH old/new still remain \`requested2/applied1/pendingtrue\` due the **second cumulative native M2 APPLIED witness veto** \`capacity_censored==0\`. **FAIL**, not erased. Artifact12595970410 sha25608681bd94fb01dd339f097d073213b1b626b10fdb5fc968e1107a16e1d830c24.
- **W74** [Action40183982270](https://github.com/lly8666/wbd-next/actions/runs/40183982270): genuine C2S20% line-loss regression on intermediate native seamless cutover PASS_SCOPED, correct rapid UP Balanced3→Maximum6 and full one-grade down both, no source TUN drop. Artifact12595266940 sha256340f2bdd136547621095839cd03a23aba579835812f7d478daa9708786aa3bc0.

**Final exact native candidate:** FEC-owned patches \`ca56932a\` (Go 16s native recent-delta HOST validity), \`7586374c\`+\`57c80f9f\` (original FEC bounded source/parity transition on settled native M4; old parity cannot satisfy new revision APPLIED), \`7ad0ba91b656ff8e9ee965d0c093a18e048971fb\` (native original M2 APPLIED witness from genuine >=16s capacity-quiescent time plus **NEW** post-capacity M4 DATA positive and authenticated reverse kind1, never reset cumulative counter, fail closed on rollback/saturation). Exact ARM64 build [Action40185113624](https://github.com/lly8666/wbd-next/actions/runs/40185113624) **SUCCESS**, frozen artifact12596370712 sha256 \`ab1407ccc5dd85c3a66c885cd410dbdd27fa7059461f18647d8ca6b41ce7384e\`; original native auth tests and full build passed. No new peer capacity wire format, no fake/positive ACK, no modifications to default outer recovery, no host-wide synthetic throttling.

**W75 [sameVM Action40185308539](https://github.com/lly8666/wbd-next/actions/runs/40185308539), artifact12595962862 ZIP sha256 \`78e34676494447068c194778fbbb86a9829e8a48c86ccf7381d6decbf8eb34da\`: A intermediate source57c80f9f vs B final7ad0ba91, SAME VM sequential, identical test request, authentic originally committed binary A then B.**

| Measured point | A, expected old defect | B, corrected final native M2 |
|---|---|---|
| Harness outcome | **FAIL**, authentic native apply never completed | **INCONCLUSIVE** solely for real upstream source TUN TX loss; **0 harness failures** |
| Measured 60Mbps main UDP missing C2S / S2C | 937 / 511 | 426 / 485 |
| Measured steady source TUN TX kernel loss client / server | 497 / 129 | 55 / 92 |
| Warmup source TUN TX loss (separate!) client / server | 133 / 185 | 1034 / 185 |
| 90s recovery 6Mbps UDP main missing C2S/S2C | 0 / 0 | **0 / 0** |
| Actual Auto UP request during host pressure | 0 both | **0 both** |
| Actual Auto DOWN requests client / server | 1 / 1 but never applied | **5 / 5**, each on authentic \`VALID\` |
| Native final client AND server | **requested2/applied1, High4, pendingtrue** | **requested6/applied6, Light0, pendingfalse** |
| Native end-to-end evidence | TRUE M2 and parity, stalled APPLIED | TRUE M2 and original new source+parity sent, actual FEC TUN recovered735 client/370 server, Stop owned-clean |
| Native M2 lifetime \`capacity_censored\` | nonzero | **still nonzero**, no clearing or reinterpreting it as ACK |

B correctly tracked client **48 HOST_CAPACITY / 47 VALID / 25 UNKNOWN** and server **51 / 44 / 24** quality windows. B old post-pressure native M2 witness became eligible only on positive *new* authenticated reverse feedback, with genuine client1,666,768 / server1,667,046 positive samples and reverse reports client73,077/server72,920. Old parity is retained and cannot count as applied new parity. B both source queues attempted=queued ~3.19 million; FEC parity **not universally lossless** (client planned2,456,365/sent2,446,920, server planned2,463,098/sent2,452,273); zero RX *capacity* rejects or pressure eviction but some time-based expiration. Peak CPU process ~75.04/75.73 seconds over 180s phases; distinct actual host PSI/traffic across A/B, so **do not claim causal CPU or packet-loss percentage win** from two unseeded sequential trials. The overall W75 Action is failure because the deliberate A old leg is FAIL; this is not B failure. B service overall cannot be called green due to real TUN drops, though the **scoped false-UP / native gradual-down after self-overload question is answered PASS**.

**W76 [Action40185321854](https://github.com/lly8666/wbd-next/actions/runs/40185321854)** independently reuses the *exact B frozen artifact/source* in original 8Mbps authenticated IID C2S 2%30s→20%60s→1%90s: **PASS_SCOPED_OBSERVATION**. Client real VALID **Balanced3→Maximum6** prompt UP, then 6→5→4→3→2→1→Light0; S2C 5→4→3→2→1→Light0. Native final client requested=applied10/pendingfalse and server6/6/pendingfalse. During actual 20% phase main UDP missing C2S108, S2C5; 1%-recovery missing 0 both; client/server source TUN0; real original native M2 positive sample143386/154122, FEC recovered TUN489/11270, outer DATA retrans0, Stop-clean. Artifact12596107096 ZIP sha256 \`79706d9bf5fb2884be1a3c1e2db2f9e34f471ae0beb675ed9bfa2518c9dd6615\`.

**Exact scope and explicit STOP:** The original sender-host resource-overload misfreeze and its native APPLIED blockage are fixed on both endpoint roles in the tested 6→60→6Mbps small-PPS Linux ARM64 product, preserving truly high-line-loss fast UP. This is NOT a general 60Mbps packet-loss-free capacity certification. In particular, a *remote receiving host* persistently overloaded without a peer-authenticated host-capacity signal could still masquerade as wire loss; these self-sender-side tests DO NOT close that edge. The historical W49/W50 100Mbps mixed-high-loss TCP backpressure, Game/Windows, original FEC real 65KiB TUN, and exact combined-source integration are NOT qualified. Preserve independent \`experiment/fec-network-tuning\`, \`scoped_integration_review_ready=true\`, \`merge_ready=false\`, \`capacity_stop=true\`; no cross-team status overwrite, no main merge, **stop high-load fanout**. Full machine-readable archival receipt: \`docs/evidence/fec-network-work/20261025-W69-W76-real-self-overload-Auto-capacity-recovery-AB-SCOPED.json\`.


## W77–W78 — Post-overload safe-boundary regression, mixed real reordering/duplication and old FEC parity revision (PASS_SCOPED)

The W69–W76 own-host capacity rescue and eventual native \`APPLIED\` were already closed. One independent **finite** gap remained: a real reordered/duplicated original outer link with odd FEC source lengths and authentic first-TUN delivery, plus a native three-class mid-flight revision fence. Not a new capacity ladder, not a merged source. All original DATA retransmission remains truly OFF, FEC parity/real M2 authenticated and independently measurable.

**W77** [Action40189681443](https://github.com/lly8666/wbd-next/actions/runs/40189681443) PASS_SCOPED with contract Action40189681393 PASS, exact frozen source \`7ad0ba91b656ff8e9ee965d0c093a18e048971fb\`, prebuilt ARM64 artifact12596370712. One real scenario: Fixed **Medium2** 8Mbps each, UDP96% + two real TCP flows4%, 64/65/127/255/256/257/511/512/513/899/900/901/1287B, 20Hz independent64B probes. First20s clean75ms, middle60s **5% IID loss + 10% reorder + 2% duplicate +15ms jitter**, final30s clean (both directions), 15s warmup,30s drain. Real netem recorded lost client4.8946%/server4.8427% middle; not merely a request flag.

| W77 on true original TUN+TLS | C→S | S→C |
|---|---:|---:|
| Middle phase main UDP sent / missing | 124328 / **6** (0.00483%) | 124327 / **2** (0.00161%) |
| Main UDP first arrival p99 middle | 98.9ms | 98.3ms |
| Main UDP missing before/after | 0 / 0 | 0 / 0 |
| Real TCP 4% missing across phases | 0 | 0 |
| TCP first arrival p99 middle | 164.1ms | 189.8ms |
| Small UDP subset missing middle | 3 / 52206 | 0 / 52206 |
| 20Hz independent 64B probe missing middle | 0 / 1190 | 1 / 1191 |
| Genuine recovered TUN sources at RECEIVING endpoint | server9510 | client9374 |

Native both Fixed readback \`requested=applied=1 profile2 pendingfalse\`; original client parity planned=sent108449/108449, server108504/108504, 0 expiry/pressure. Positive authenticated native M2 sample client251588/server251807 with reverse kind1 reports40519/40629 and mean138565/138525µs. Real application UDP duplicates delivered **0** in both directions although old RX capacity telemetry \`reject_conflict=2913 client /2883 server\` under deliberately duplicated/reordered traffic. Those rejects were **not suppressed**, and no decoder capacity rejection/pressure eviction occurred; RX age-evicted 21957/21875 is independent bounded lifetime expiry, not proof of capacity failure. Both source TUN TX/root drops0, native original outer DATA retrans0, Stop drained and owned namespaces removed. CPU client19.28/server19.27 seconds for measured110s, RSS peak23.88/23.98MB; no same-VM CPU improvement claim, host contention warning documented. Full ZIP artifact12597329553 sha256 \`efd73dc976e16e96ce3d9df2c39329ce3620deb3cff967806920eef3ea89bbc4\`.

**W78** FEC-owned \`crates/wbd-engine/src/v4_fixed_stream.rs\` TEST-ONLY source \`4a77104b23363bc1d1802223643d6ab441d7f019\`, focused native regression \`m0_auto_prior_three_classes_sealed_same_owner_no_cross_revision_parity\`: three simultaneously open old Strong rev10 source classes 65/300/1100B; native rev11 retains old per-job math and exact old parity, new fresh source uses block id4 without waiting; second rev12 rejected while old queued parity remains; after three genuine copied old rows, rev12 succeeds and the previous rev11 parity keeps revision11; Stop twice drains owner/arena. ARM64 original fixed native test contract [40189755295](https://github.com/lly8666/wbd-next/actions/runs/40189755295) **SUCCESS**, exact-source full original Go/Rust ARM64 build [40189755361](https://github.com/lly8666/wbd-next/actions/runs/40189755361) **SUCCESS**, artifact12596464645 sha256 \`2a02a7398f9d716243f8172d918789ead98220d9805e3c1e25676407067b072f\`. W78 contains test only, no product semantic patch or comparable A/B CPU sample; W77 correctly uses original frozen 7ad0 product, not the separate W78 build.

**Closure:** Scoped Linux ARM64 authentic FEC-only representative reordering, replay-safe first delivery, odd packet size/class boundary, parity and old→new revision fence checked. Not proof of Gilbert-Elliott burst correlation, 65KiB FEC-over-TUN product, Windows/Game, sustained remote receive-host congestion or exact combined main/network-branch integration. No product defect reproduced: no unjustified FEC policy changes. Scoped integration review may continue, but \`merge_ready=false\`, \`capacity_stop=true\`; no main merge or other network team alteration. Full exact-source machine-readable artifact \`docs/evidence/fec-network-work/20261025-W77-W78-reorder-duplicate-multiclass-original-arm64-PASS.json\`.

## W79–W83 — Finite Gilbert–Elliott burst-loss envelope on original ARM64 FEC-only (scoped closure)

The previous W69–W78 host-capacity and replay/multi-class work is CLOSED. User requested more independent test cases; the next missing dimension was packet-**correlated loss** rather than IID or high rate. No original product semantic source modified. Every run reuses EXACT frozen source `7ad0ba91b656ff8e9ee965d0c093a18e048971fb`, ARM64 [build40185113624](https://github.com/lly8666/wbd-next/actions/runs/40185113624), artifact12596370712 ZIP sha256 `ab1407ccc5dd85c3a66c885cd410dbdd27fa7059461f18647d8ca6b41ce7384e`, original TLS+native M1/M2-auth/M3-parity/M4+TUN, two real endpoint directions at **8Mbps each** (96% real UDP + two TCP streams totaling4%), 75ms each way and assorted 64/96/160/255/256/257/512/900/1287B bodies with separate 64B probes. The original outer DATA repair is truly OFF; actual DATA retransmitted **0** all runs, FEC repair parity independently active.

The actual Linux netem [Gilbert–Elliott gemodel documentation](https://manpages.debian.org/trixie/iproute2/tc-netem.8.en.html) uses `[P,R,1-H,1-K]`. With (1-H)=100%,(1-K)=0%, `P=1%,R=19%` models a steady **5%** bad-state fraction and expected consecutive bad run ~5.26 packets; `P=3%,R=17%` models steady **15%** with mean bad run ~5.88; `P=6%,R=34%` still steady **15%** but mean run ~2.94. Expected run lengths are **model expectations**, not packet-capture proof; netem per-phase actual outer losses are recorded. We never force product grade from qdisc truth or turn M2 UNKNOWN into a clean ACK.

| Exact original Action (one scenario each) | Real netem burst model and measured loss | Stress main UDP C→S / S→C loss after drain | Functional and business interpretation |
|---|---|---|---|
| **W79** [40191027046](https://github.com/lly8666/wbd-next/actions/runs/40191027046) | Fixed Medium2 GE `[1,19,100,0]`; actual outer lost5.271%/5.093% | **2511/88132=2.849%**; **2466/88134=2.798%** | Action **PASS_SCOPED_OBSERVATION** only because loss gate deliberately set **100% for diagnostic**. NOT a 1% residual qualification; partial k/parity and TUN functional, final fixed requested=applied1 profile2 |
| **W80** [40191030800](https://github.com/lly8666/wbd-next/actions/runs/40191030800) | Fixed Maximum6 GE `[3,17,100,0]`; actual lost14.805%/14.937% | **1182/88132=1.341%**; **1349/88135=1.531%** | Action **FAIL** ONLY due both strict **1% UDP loss gates**. **Preserve** as real long-burst service negative, not compile/TUN/capacity/decode failure |
| **W81** [40191033811](https://github.com/lly8666/wbd-next/actions/runs/40191033811) | Auto C→S IID1%30s→GE~15%60s→IID1%120s, S→C0→1→0%; actual C→S14.648% high | C→S high **2688/88162=3.049%**; S→C high3/88163. Recovery C→S1/176235 and S→C0/176234 | **PASS_SCOPED** Auto feedback/applied curve (transition loss allowed, high-phase 1% service NOT claimed). Genuine VALID C→S 5→4→3→4→Maximum6 on two rising windows then 6→5→4→3→2→1→Light0; native client requested=applied11, server6; pendingfalse both |
| **W82** [40191413910](https://github.com/lly8666/wbd-next/actions/runs/40191413910) | Fixed Maximum6 GE `[6,34,100,0]`, **same stationary ~15% but shorter expected burst**; actual14.935%/14.982% | **143/88131=0.162%**; **193/88132=0.219%** | **PASS_SCOPED** actual strict main UDP≤1% /small UDP≤3%; no host-capacity or decoder anomaly. W80/W82 different Actions VM, cannot claim causal cross-VM performance improvement |
| **W83** [40191819998](https://github.com/lly8666/wbd-next/actions/runs/40191819998) | **SAME frozen Maximum6 process on SAME ARM64 VM:** clean15s→long GE15%45s→clean15s→short GE15%45s→clean30s. Actual outer long14.584%/14.678%; short15.091%/15.006% | **LONG** C→S873/66100=1.321%, S→C861/66100=1.303%. **SHORT** C→S142/66099=0.215%, S→C132/66099=0.200% | Action **PASS_SCOPED for the explicitly short-only 1% loss gate**; long-phase above1% remains NOT qualified. Same original VM/process, fixed order unseeded; consistent evidence for burst-length sensitivity, not a universal deterministic recovery guarantee |

**Native independent evidence:** Fixed W79 requested/applied1/1 Medium2; W80/W82/W83 requested/applied1/1 Maximum6, all pendingfalse. FEC real planned/sent parity counts W79 client84457/server84385; W80 client273057/server273244; W81 client262438/server112753; W82 client273334/server273291; W83 client333680/server333321: **each planned==sent**, expired0, unknown-capacity0. Original FEC TUN actually recovered W79 client2244/server2341; W80 client12796/server12393; W81 client934/server13727; W82 client14124/server14139; W83 client19910/server19980. Actual authenticated native reverse M2 positive data exists across runs; W81 95 VALID/45 UNKNOWN C→S and 102 VALID/31 UNKNOWN S→C, rising UP only on authentic VALID, not a synthetic witness. All scenarios original source TUN TX drops0, receiver `reject_capacity=0`, `pressure_evicted=0`, decoder rejected0, real inner TCP missing0, Stop drained & owned namespaces gone. Sparse independent 64B probes **DO miss packets**, including W80 14/1190 and29/1189, W83 long19/892 and14/893, short6/892 and4/893; do not claim absolute zero loss because TCP0/clean0.

**Negative interpretation:** W80 long correlated runs remain above the chosen 1% service target under real Maximum; do NOT erase failure or extrapolate IID30% residual math to correlated bursts. W82 and W83 independently show that shorter expected runs at approximately the same aggregate 15% loss meet the gate; finite parity cannot universally recover arbitrarily long erasure strings, and there is NO observed capacity rejection, failed native parity, fake applied or demonstrated timely-recoverable group silently dropped. Therefore no justified FEC product/outer-network policy patch. These are one-shot unseeded GE trials, so the difference isn't a promised universal threshold; W83 is within-VM sequential but its phase order isn't randomized. The user-approved Auto fast authentic UP, per-grade gentle DOWN and acceptable transition losses remain intact.

**Remaining work / finite STOP:** a sustained **remote receiver host** exhaustion authenticated signal (not covered by LOCAL sender M2 capacity), actual 65KiB source through FEC TUN product, Windows/Game native product integration, W49/W50 historical mixed100Mbps high-loss TCP backpressure, and an exact assembled outer-ON + FEC qualification remain separate. Do not resume high-rate trial ladder or claim Game/Windows/full merge. Keep `scoped_integration_review_ready=true`, `capacity_stop=true`, `merge_ready=false`; no main branch, network matrix status, or external repair edits. Full itemized ZIP digests and provenance: `docs/evidence/fec-network-work/20261025-W79-W83-GE-correlated-burst-original-arm64-SCOPED.json`.

**W90回滚后二次核验：** [ARM64产品原生完整构建/功能检查 40211941478](https://github.com/lly8666/wbd-next/actions/runs/40211941478) **SUCCESS**，原生 artifact `12605274526` ZIP SHA256 `ba846bca14a07f8bcfdefef423151b9075a05c4cfa2fad49332c22c6ab83a591`；[最高档修复行契约 40211941508](https://github.com/lly8666/wbd-next/actions/runs/40211941508) **SUCCESS**。该核验是回滚后原Linux产品构建/功能检查，**不是 Game+FEC 的有效业务资格**。历史 W90 六条真实业务失败保留，Game+FEC当前仍不支持。

**W91后继提交保护说明：** 在本轮 `b5052654` 精确回撤之后，另有独立[W91提交 19942fab](https://github.com/lly8666/wbd-next/commit/19942fab71b1b84d5caa31254e9c3d60a36d8366) 只对 Game **OFF** 的 `v4_game_lane.rs`、`v4_game_public_kernel.rs` 做 RX错误分类，并留单独 W91 日志；当前 HEAD 因此与 W90 前旧源码在这两处已存在后继差异，**不能说当前HEAD全部15个blob仍与旧源码一样**。`b5052654` 原子回撤时15个blob逐字节一致的核验依然有效。本轮没有覆盖或回滚W91，原回滚构建 [40211941478](https://github.com/lly8666/wbd-next/actions/runs/40211941478) 属于 **W91之前的 b5052654**，不当成W91最新提交已验证。W90公开Game+FEC已撤、真实业务六FAIL的结论不变。

## W90–W97 | Original Linux Game2/Game4 architecture (independent FEC scope; provisional, no main merge)

**Product boundary.** W90's fixed0/fixed6 Game+FEC public candidate and subsequent parity scheduling revisions suffered **six** real ARM64 business FAILs (TCP bootstrap or clean UDP/TCP) and were atomically withdrawn in `b5052654975b`; retained in `docs/evidence/fec-network-work/20261025-W90-GameFEC-product-candidate-FAILED-rollback.json`. Native RS/AES tests alone did NOT qualify that product. Current Game2/4 *public* code remains `game_fec=off`, distinct from Normal Fixed/Auto and outer DATA-repair policy. Do not claim repaired Game+FEC from Game OFF tests.

**W91:** real [Game2](https://github.com/lly8666/wbd-next/actions/runs/40212643000) and [Game4](https://github.com/lly8666/wbd-next/actions/runs/40212646332) FEC OFF, 3Mbps each way, 96% UDP+4% real TCP, zero artificial loss: both **PASS_SCOPED**, 100% injected/delivered, p99~77.5ms, no TCP backpressure or source TUN loss, Stop clean. Game RX now counts AEAD tag failures separately from authenticated per-lane replay and malformed/capacity errors.

**W92:** Linux one-cBPF-filter-per-authenticated-lane 4-tuple eliminates unrelated raw socket userspace packet copies without changing AEAD/PN/generation. Same VM Game4 old/new [AB40213471471](https://github.com/lly8666/wbd-next/actions/runs/40213471471) and [BA40213802360](https://github.com/lly8666/wbd-next/actions/runs/40213802360) showed ~9–10% lower CPU at unchanged true UDP/TCP delivery and p99; Game2 ~1% inconclusive. This is kernel exact prefilter, **not** a shared single raw FD nor true `recvmmsg`.

**W93:** TX and shared RX state separated so RX does not need `GameAdapter` TX lock around raw sends; retains one shared cross-lane dedup and per-lane AEAD/PN. Exact native + two sameVM clean Game2/4 [40214330740](https://github.com/lly8666/wbd-next/actions/runs/40214330740) / [40214339875](https://github.com/lly8666/wbd-next/actions/runs/40214339875) **PASS_SCOPED**; CPU neutral (Game4 slight +RSS), justified by no TX lock HOL.

**W94:** bounded TX seal scratch reuse and authenticated RX duplicate precheck saved hot-path allocations; exact native [40214830539](https://github.com/lly8666/wbd-next/actions/runs/40214830539) + Game2/4 clean sameVM [40215055396](https://github.com/lly8666/wbd-next/actions/runs/40215055396) / [40215059452](https://github.com/lly8666/wbd-next/actions/runs/40215059452) **PASS_SCOPED**, but small CPU changes diverge (Game2 +3–4%, Game4 −2–3%), so **no proven CPU gain**. W95 full original independent20/lane1-blackhole 3Mbps new-source [Game2 40246424032](https://github.com/lly8666/wbd-next/actions/runs/40246424032) / [Game4 40246427496](https://github.com/lly8666/wbd-next/actions/runs/40246427496) **PASS_SCOPED**: Game2 IID20 UDP missing626/655 ≈p²=4%, Game4 missing23/27 ≈p⁴=0.16%; BOTH blackhole/clean phases zero missing, true TCP all phases full delivery, Stop clean. FEC OFF does not claim parity recovery.

**W96:** actual TUN write was previously AFTER logical Game dedup commit. Independent RX owner now prepares authenticated source in bounded per-lane pending, releases lock for genuine TUN write, and commits bitmap only on successful TUN result; TUN error frees pending for other still-unprocessed authenticated lane copy. Exact native [40246704747](https://github.com/lly8666/wbd-next/actions/runs/40246704747) **SUCCESS** synthetic failed write + alternate lane and pending duplicate tests; exact ARM64 sameVM clean [Game2 40246931539](https://github.com/lly8666/wbd-next/actions/runs/40246931539), [Game4 40246935612](https://github.com/lly8666/wbd-next/actions/runs/40246935612) **PASS_SCOPED** on true 3Mbps UDP/TCP, zero loss/TCP backpressure, p99≤77.6ms, Stop clean. Game2 CPU +4–5% from extra state synchronization, Game4 CPU approximately neutral; retain for correctness, not CPU saving. W97 same-load exact-source weaknet verified: [Game2 40247215239](https://github.com/lly8666/wbd-next/actions/runs/40247215239) and [Game4 40247219774](https://github.com/lly8666/wbd-next/actions/runs/40247219774) **PASS_SCOPED**. Under independent20 Game2 UDP missing665/678 and Game4 20/20, consistent with p²/p⁴; lane1 blackhole Game2 C→S missed **2** (not zero), S→C0, Game4 0/0; both clean phases 0/0; real TCP injected=delivered all phases, no backpressure or source TUN drops, Stop drained. Game2 IID20 TCP p99 reached ~788/527ms, measured not concealed; no paired CPU old/new on damaged phases.

**Limits:** W90 fixed Game FEC still unsupported; FEC Auto remains Normal-only. Linux Game tests do not equal Windows or physical-device qualification, and distinct-VM CPU-s must not be compared causally. Outer Game MULTILANE repair ledger is NOT_APPLICABLE. Normal FEC-only historical Fixed/Auto positive scope and long GE failures remain unchanged. `capacity_stop=true`, `merge_ready=false`; no main merge, no external network-role status modification. Machine-readable receipts W91/W92/W93/W94/W95/W96 in own evidence folder.

## W98 — Shared Game fixed6 reconnected to original TX/RX owner: first real Linux no-loss TCP/UDP PASS_SCOPED

Original W90 six Game2/4 fixed6/fixed0 real TCP/clean failures remain **valid old-source negatives**. W98 reuses RS16 math while separate shared Game TX-FEC and RX-FEC owners protect original 2/4 individually AEAD-authenticated lanes and original TUN write acknowledgement; no Game Auto, new lanes or reintroduced shared TX/RX lock. Source-first original M4 copy before finite parity work and bounded RX multi-source delivery passed native [40254464042](https://github.com/lly8666/wbd-next/actions/runs/40254464042) and [40255014279](https://github.com/lly8666/wbd-next/actions/runs/40255014279). Original Go TLS protected profile mismatch test [40255724717](https://github.com/lly8666/wbd-next/actions/runs/40255724717) **SUCCESS** after a test-only cgo linker fix; earlier Action 40255456429 failed at missing cgo link flags, **NOT** TLS assertion. Real tested product **`c18de0fa79f529c349b6546635f3c6b62aa01b1c`**, ARM64 build [40255431613](https://github.com/lly8666/wbd-next/actions/runs/40255431613), artifact12621844471 SHA256 `85e50a70ef44306fe5a6f913010d57568cc01b652830be09d473cbd7b2248ac6`.

- [Game2 fixed6 clean Action40255806409](https://github.com/lly8666/wbd-next/actions/runs/40255806409) **PASS_SCOPED_OBSERVATION**: each way injected=delivered UDP2.8798264Mbps and real TCP0.1198944Mbps; p99 UDP77.5–77.6ms, TCP78.1ms; zero missing/backpressure/TUN drops; Stop drained. Both genuine original Go TLS `GAME_FEC_APPLIED fixed profile6`. Client/server FEC planned 29904/29922 = actual copied/sent, source21849/21850, recovered0 (clean), expired/failed0. CPU2.73/2.73s, RSS26.6/26.9MB, outer TX18.06Mbps per side, CPU/effectiveGiB390.88.
- [Game4 fixed6 clean Action40255813118](https://github.com/lly8666/wbd-next/actions/runs/40255813118) **PASS_SCOPED_OBSERVATION**: each way UDP~2.88Mbps and real TCP0.1198944Mbps fully delivered; p99 UDP77.9ms, TCP78.0–78.2ms; zero missing/backpressure/TUN drops; Stop drained. Both TLS FEC fixed profile6 actually applied. FEC planned/copies/sent client29896 server29866, sources~21834–21855; decoder recovered0 at no loss; expired/failed0. CPU client3.98/server4.07s, RSS39.2/38.9MB, outer TX36.14Mbps per side, CPU/effectiveGiB569.75/582.74.

Both real TUN MTU 1398 follows **exact** negotiated wire1460−record31−Game16−FEC15; log `fec=off` describes separate Normal mode, whereas authenticated `GAME_FEC_APPLIED mode=fixed profile=6` verifies Game FEC on. A green harness is backed by original M4 real parity/counters and true TCP/UDP application receipts. Bandwidth/CPU overhead is material; different VMs, **no direct paired Game OFF vs Game fixed6 performance claim**. Per-lane independent loss, shared correlated bursts, blackholes and authentic FEC recovered→TUN at real network remain **NOT_RUN on W98**. `--outer-repair=off` for Game still explicitly unsupported, so cannot claim true FEC-only outer DATA retrans disabled; Normal fixed/auto historical off readback separate. Windows TEMP_SKIPPED, capacity_stop=true, merge_ready=false. Machine-readable receipt `docs/evidence/fec-network-work/20261026-W98-Game2-Game4-fixed6-real-clean-ARM64-PASS-SCOPED.json`.

## W99–W100 — Original Game fixed-FEC real weaknet recovery and Light profile clean passes

W98 **fixed6** two genuine no-loss Game2/4 TCP+UDP native product passes are followed by exact same immutable `c18de0fa79f529c349b6546635f3c6b62aa01b1c`, original TLS `GAME_FEC_APPLIED mode=fixed profile=6` on BOTH endpoints and actual native RS16 + original M4/TUN. Both cases keep 3Mbps each direction mixed 96% UDP+two TCP flows4%, 75ms one-way, original existing W97 loss wave: clean15s→each independent lane20% drop30s→lane1 blackhole30s→clean15s. One independent Action/scenario/VM, no added pressure.

[W99 Game2 40256521889](https://github.com/lly8666/wbd-next/actions/runs/40256521889) **PASS_SCOPED_OBSERVATION**: 20% phase **0/0 missing UDP** despite Game OFF W97 ~4% missing; one-lane blackout **0/0**; both clean **0/0**; *all phases genuine TCP fully injected/delivered, zero backpressure*, UDP p99 IID20=83.0/83.2ms and TCP84.6/85.3ms, active zero-delivery intervals per workload about70–80ms; TUN source drops0, Stop drained. Receiver authenticated FEC recovered candidates client776/server810; parity plan=offered=copied=sent client89182/server89223; expired0. CPU client/server9.65/9.69 seconds for measured90s; CPU/effectiveGiB307.01/308.28; RSS 26.7/26.9MB, PSI2.7%, outer TX13.85Mbps per side. Native aggregated FEC failure **89/92**, not zero and unclassified.

[W99 Game4 40256529112](https://github.com/lly8666/wbd-next/actions/runs/40256529112) **PASS_SCOPED_OBSERVATION**: 20% phase0/0 UDP missing, blackhole0/0, clean0/0, true TCP fully injected/delivered all phases, zero backpressure; IID20 UDP p99 77.7/77.6ms, TCP77.8/77.9ms, Stop clean. FEC recovered candidates client84/server87; parity planned/copied/sent89284/89352, expired0; native aggregated FEC failed267/263, **not yet classified as benign**. CPU17.49/17.64s, CPU/GiB556.44/561.21, RSS39.5/38.8MB, PSI6.78%, outer TX30.75Mbps. No cross-VM causal performance comparison.

Recovered_candidate is a native decoder metric, not separately tagged recovered-source successful TUN receipt; corroborated by authentic no-missing business and original total TUN deliveries, **not misrepresented as exact per-source write confirmation**. Normal original outer DATA repair-zero readback does NOT transfer to Game, where `--outer-repair=off` still explicitly UNSUPPORTED. Correlated GE long bursts and Windows NOT_RUN; do not claim universal zero loss.

[W100 Game2 fixed0 clean 40256692692](https://github.com/lly8666/wbd-next/actions/runs/40256692692) and [Game4 fixed0 clean 40256700110](https://github.com/lly8666/wbd-next/actions/runs/40256700110) both **PASS_SCOPED** on real 3Mbps/dir zero artificial loss, UDP/TCP injected=delivered in both directions, p99~77.5ms, Stop clean. Original TLS `GAME_FEC_APPLIED fixed profile0` both sides, parity offered=copied=sent Game2 client7042/server7015, Game4 6920/6913, failed0/expired0; Game2 CPU2.01/2.06s RSS~26MB; Game4 CPU2.89/2.93s RSS~38–39MB. One Game2 pre-Stop counter snapshot retains4320B source (partial block in-flight) but owned Stop drained—NOT automatically a lifecycle leak. These clear W90 old fixed0 clean startup failure on new implementation. Weaknet for fixed0 NOT_RUN, no new high-load cases.

Machine-readable `docs/evidence/fec-network-work/20261026-W99-Game2-Game4-fixed6-IID20-blackhole-PASS-SCOPED.json` and `20261026-W100-Game2-Game4-fixed0-real-clean-PASS-SCOPED.json`. Scope complete only for fixed0 clean and fixed6 independent20/one blackhole, not correlated long GE, larger MTU, Windows/physical, outer-repair-off Game, nor merge-ready. `capacity_stop=true`, `merge_ready=false`.

## W101 — Real Game fixed6 categorized decoder rejects (2026-10-26)

Source `8afc2b8f443dd59edc912fef24b5fffa92e3a6d7`; first W101 source `24c5b7ec` failed both native Actions [40257476029](https://github.com/lly8666/wbd-next/actions/runs/40257476029), [40257476050](https://github.com/lly8666/wbd-next/actions/runs/40257476050) for a Rust **test annotation compile error**, not runtime quality: an associated `#[test]` under `impl`. Single test-only fix `8afc2b8f` native [40257758450](https://github.com/lly8666/wbd-next/actions/runs/40257758450) **ALL PASS** with added categorized error regression; exact artifact12622774367 ZIP SHA256 `80f65de67e9a89ba961f3d18a722c53cee8911ce19f0a1315f98d448713f9772`.

One unchanged-load real [Game2 fixed6 40258049780](https://github.com/lly8666/wbd-next/actions/runs/40258049780) **PASS_SCOPED** (same W99 waveform/seed, distinct runner): real 3Mbps each way mixed 96% UDP +2 TCP flows, 75ms one-way, clean→each-lane independent20%→lane1 blackhole→clean, full genuine injection and delivery, no missing packets, no TCP backpressure, source TUN drop0, Stop drained. FEC source candidates client64707/server64659, recovered candidates741/799. Client/server parity planned=offered=kernel-copied=sent 89489/89358, expired0, meaningful parity-to-business. FEC total `failed` client102/server100, **classified** after original per-lane AEAD and shared Game logical identity: `rx_invalid`73/78; `rx_conflict`29/22; `rx_capacity`, `rx_codec`, `rx_state`, `rx_frame` all0; actual `auth_rejected=0`. Therefore **not** AEAD and no observed codec/memory saturation, but `rx_invalid` still includes retired/old/malformed cases, not proven benign.

IOD measured p99 independent20 UDP83.3/82.9ms, TCP84.9/85.1ms; longest active zero UDP70ms/TCP80ms. CPU9.91/10s, CPU/effectiveGiB315.28/318.15, RSS26.83/26.69MB, PSI peak2.86%, outer interface bytes155862745/155810373. Different VM from W99: no CPU delta claim. Scope: Linux Game2 fixed6 under independent loss / one-lane blackout only; Game4 W99 actual base source qualified independently, Game4 W101 categorized source NOT_RUN; no shared long correlated GE, idle high-parity silent tail, real 65KiB or Windows/physical claim. Outer Game --outer-repair=off remains UNSUPPORTED, Normal FEC-only OFF separate. See machine-readable [W101 receipt](https://github.com/lly8666/wbd-next/blob/experiment/fec-network-tuning/docs/evidence/fec-network-work/20261026-W101-Game2-fixed6-RX-reasons-IID20-blackhole-PASS-SCOPED.json). `capacity_stop=true`, `merge_ready=false`.


## W102 — Game2 fixed6 shared long GE correlated-loss boundary (2026-10-26)

Exact `8afc2b8f443dd59edc912fef24b5fffa92e3a6d7` ARM64 frozen build [40257758450](https://github.com/lly8666/wbd-next/actions/runs/40257758450), artifact12622774367 SHA256 `80f65de67e9a89ba961f3d18a722c53cee8911ce19f0a1315f98d448713f9772`. One separate genuine [Game2 fixed6 Action40258651816](https://github.com/lly8666/wbd-next/actions/runs/40258651816), artifact12623970569 SHA256 `69774b68d0bfe41192c24489ff59a833c44d9d075f53768af2274a8391514ba1`, **PASS_SCOPED_OBSERVATION** under clean gates, but **correlated high-loss phase does not meet 1% target**. Reused original W89 waveform without higher load: 3Mbps per direction UDP96% plus actual 2 TCP flows, 75ms, clean15s→shared GE(3,17,100,0)45s→clean15s.

Shared GE injured interval: UDP injected2.880Mbps each, delivered2.806/2.810Mbps, missing **434/438** original UDP packets (~**2.56%/2.43%**); sparse small UDP missing69/86 of 9424 per direction. Both clean phases **0 missing**; real TCP all phases genuinely injected/delivered, no backpressure, GE TCP p99 **291/402ms**, post-GE TCP p99 **110/166ms**, GE UDP p99~85.4ms, no business-wide stopped receipt more than20ms within the inspected phase. FEC authenticated recovered candidates **3057/3037** at respective endpoints; scheduled=offered=original M4 copied=sent parity **76859/76679**, failed0, expired0, classified rx_invalid/conflict/capacity/codec/state/frame all0, actual AEAD rejects0, TUN source drops0, Stop drained. CPU8.18/8.01s, CPU/receivedGiB316.71/310.37, RSS26.6/27.2MB and outer interface TX154.21/154.06MB. Host CPU PSI **33.81% peak**, 12% monitored samples above20%; runner emitted host-contention warning. **Capacity stop now applies: no extra Game4 shared GE or higher-rate pressure.**

Historical Game OFF W89 under nominally same shared GE had ~13.35/13.15% UDP missing, but W89 and W102 ran on distinct VMs with **unseeded actual loss events**; this difference is encouraging, **not** a paired causal 10-point benefit claim. Shared prolonged loss exceeds available FEC correction some intervals, so no promise of zero loss or universal no-HOL guarantee. Game outer `--outer-repair=off` is still explicitly UNSUPPORTED: outer DATA retrans0 not attested. No Windows/physical/real 65KiB or high-FEC-silent-tail scope. Evidence `docs/evidence/fec-network-work/20261026-W102-Game2-fixed6-sharedGE15Long-real-PASS-CLEAN-with-residual.json`, `capacity_stop=true`, `merge_ready=false`.

## W103–W104 | Original Game outer DATA retransmit OFF actually wired and loss-tested

Exact product SOURCE `e8b41fb49a74648e405bf23e4600e23c618596fe` [ARM64 build40260662919](https://github.com/lly8666/wbd-next/actions/runs/40260662919), frozen artifact12623678360 SHA256 `04d209b7ef1e887af6599622aaf71efc34381451c847e844cf18c2006ae9708f`. Narrow common-path adapter change: Original Go TLS Game group receives `--outer-repair=off` BEFORE native M4 driver threads, owns an immutable OFF flag, and per-lane kernel send dispatch disallows repeating/rewinding a previously *successfully* copied Game logical source/parity ID. Other lanes seal independent first copies, and FEC parity is independently offered with fresh IDs (unchanged encryption and RS16 math). Runtime successful repeated lane-copy counter is **incremented after actual raw send**, not a fabricated zero. Native group slow readback reports enabled, actual repeated copied, blocked duplicate and all fresh lane copies. No Normal V3 recovery algorithm or Game Auto alteration.

**W103 no-loss real business:** [Game2 40260913377](https://github.com/lly8666/wbd-next/actions/runs/40260913377) and [Game4 40260918778](https://github.com/lly8666/wbd-next/actions/runs/40260918778) both PASS_SCOPED; two actual endpoints report `repair_enabled=0`, `outer_data_retransmitted=0`, `blocked_duplicate=0`, independent first lane copies 103586/103486 (Game2) and 207020/206468 (Game4). Original Game fixed6 parity copied and sent29935/29906 and29907/29816 separately. Genuine 3Mbps each direction, 96% UDP+real TCP, no application missing/backpressure or source TUN drops, p99≤78.2ms, Stop drained. Host Game4 CPU PSI peak31.09% (caution; no load increase).

**W104 real impairment same exact binary:** [Game2 40261223312](https://github.com/lly8666/wbd-next/actions/runs/40261223312), [Game4 40261228792](https://github.com/lly8666/wbd-next/actions/runs/40261228792) both PASS_SCOPED under existing 3Mbps each direction 75ms waveform: clean15s→each-lane independent20%30s→one-lane blackhole30s→clean15s. **All phases genuine bidirectional UDP/TCP fully injected/delivered, no missing, no TCP backpressure, Stop drained.** Both endpoints still native `repair_enabled=0` and **actual outer copied retransmits0**, first lane copies Game2 266043/265992, Game4 574074/573786. Distinct FEC recovery candidates Game2 765/789 and Game4 60/72; parity planned=copied=sent Game2 89683/89658, Game4 88977/88939, expiry0. Decoder failed counts Game2 97/123, Game4 241/273, all observed codec/capacity0; invalid/conflict separate, **not AEAD**. CPU-s Game2 9.81/9.87, Game4 16.73/16.97, different VMs not causal cross-mode comparison. Runner PSI peaks2.88%/6.1% damaged; no higher load launched.

Unlike the old Game product (which had no one-lane Normal M2 retry ledger), W103+W104 now give explicit **disabled M4 gate and actual send-path counters**. Game ON still is not a claim of active Normal V3 DATA retry capability. No Game Auto; only Game OFF/fixed0..6. W102 long correlated GE 2.43–2.56% residual and high host PSI remain negative, not retested at more load. Windows remains TEMP_SKIPPED, true quiet-tail and fixed1–5 new-source real qualification pending, capacity_stop=true, merge_ready=false. Original evidence W103 and W104 JSON in own directory.

## W105 — All middle Game fixed1–fixed5, real outer DATA OFF, each Game2/Game4

Exact unchanged product SOURCE `e8b41fb49a74648e405bf23e4600e23c618596fe`, build [40260662919](https://github.com/lly8666/wbd-next/actions/runs/40260662919), artifact12623678360 ZIP SHA256 `04d209b7ef1e887af6599622aaf71efc34381451c847e844cf18c2006ae9708f`. All ten separate Actions original Go TLS M4 real Linux ARM64, same genuine 3Mbps/dir 96% UDP+2 TCP flows, 75ms one way, 0% artificial loss, **PASS_SCOPED**: Game2 fixed1 [40261651100](https://github.com/lly8666/wbd-next/actions/runs/40261651100), fixed2 [40261661650](https://github.com/lly8666/wbd-next/actions/runs/40261661650), fixed3 [40262003415](https://github.com/lly8666/wbd-next/actions/runs/40262003415), fixed4 [40262014682](https://github.com/lly8666/wbd-next/actions/runs/40262014682), fixed5 [40262025973](https://github.com/lly8666/wbd-next/actions/runs/40262025973); Game4 fixed1 [40261656542](https://github.com/lly8666/wbd-next/actions/runs/40261656542), fixed2 [40261667093](https://github.com/lly8666/wbd-next/actions/runs/40261667093), fixed3 [40262008834](https://github.com/lly8666/wbd-next/actions/runs/40262008834), fixed4 [40262021170](https://github.com/lly8666/wbd-next/actions/runs/40262021170), fixed5 [40262032077](https://github.com/lly8666/wbd-next/actions/runs/40262032077). All exact native readback `repair_enabled=0`, successfully copied duplicate DATA=0, genuine FEC parity planned/copied/sent positive, FEC failed/expired=0, real UDP and TCP all injected/delivered, p99~77–78ms, Stop drained. Separate-VM CPU C/S seconds Game2 fixed1 2.04/2.08, fixed2 2.26/2.28, fixed3 2.32/2.32, fixed4 2.49/2.47, fixed5 2.67/2.64; Game4 fixed1 2.99/3.07, fixed2 3.18/3.21, fixed3 3.23/3.28, fixed4 4.14/4.21, fixed5 3.50/3.53. These are **not** paired CPU A/B. Game2/4 fixed3 host PSI peaks35.53%/34.69%: stop additional heavy loads, lower remaining 1Mbps functional cases. Real weaknet under this exact source is qualified only for fixed6 (W104), not all middle profiles. No Game Auto. Machine receipt `docs/evidence/fec-network-work/20261026-W105-Game2-Game4-fixed1to5-outerDATAoff-real-clean-PASS.json`. Windows TEMP_SKIPPED, capacity_stop=true, merge_ready=false.

## W106/W109/W110 — Original Game outer DATA OFF remaining bounded functional coverage (2026-10-26)

**Exact product remains `e8b41fb49a74648e405bf23e4600e23c618596fe`**, native Linux ARM64 [build40260662919](https://github.com/lly8666/wbd-next/actions/runs/40260662919), immutable artifact12623678360 ZIP SHA256 `04d209b7ef1e887af6599622aaf71efc34381451c847e844cf18c2006ae9708f`. No Game Auto exists or was introduced. All scenarios retain explicit native OFF switch and separate first-of-lane vs new parity identity; production Normal V3 recovery algorithm unchanged. One scenario per Action, 1Mbps each direction (one-way tests have 0 in inactive direction), genuine TLS+raw M4/TUN and TCP/UDP, not invented throughput.

**W106 lowest/off** [Game2 fixed0 40262793675](https://github.com/lly8666/wbd-next/actions/runs/40262793675), [Game4 fixed0 40262800093](https://github.com/lly8666/wbd-next/actions/runs/40262800093), [Game2 FEC OFF 40262808050](https://github.com/lly8666/wbd-next/actions/runs/40262808050), [Game4 FEC OFF 40262814726](https://github.com/lly8666/wbd-next/actions/runs/40262814726): all **PASS_SCOPED** clean 1Mbps both directions, real UDP/TCP injected=delivered, zero missing, first-arrival p99≤77.6ms, Stop drained; both real M4 outer repair_enabled0 and actual repeated DATA0. Do not imply parity must be positive when FEC OFF.

**W109** fixes original fixture false gates, not the product: W106 old quiet failure [40262822362](https://github.com/lly8666/wbd-next/actions/runs/40262822362) was due zero-rate phase being erroneously required to have small UDP cohort p99, and both W107 original one-way [40262924578](https://github.com/lly8666/wbd-next/actions/runs/40262924578), [40262931200](https://github.com/lly8666/wbd-next/actions/runs/40262931200) also incorrectly required native reverse TCP ACKs to vanish when no reverse *application* business. Real Linux guest naturally sends reverse TCP ACKs through TUN, genuinely shares FEC encoder; not retransmitted DATA. The original MTU 1Mbps Action [40262989978](https://github.com/lly8666/wbd-next/actions/runs/40262989978) had actual delivery zero loss but **INCONCLUSIVE** only for 10ms continuously paced cross-business HOL under sparse near-MTU load. New fixture explicitly scopes that HOL gate out without disabling MTU/packet/TCP/UDP/first-arrival/outer OFF gates. Native product unchanged. Harness regressions green [40264695385](https://github.com/lly8666/wbd-next/actions/runs/40264695385).

Four W109 original-product bounded retests: [dual-direction burst→10s actual no-probe silence→resume 40264740280](https://github.com/lly8666/wbd-next/actions/runs/40264740280), [C2S one-way quiet+resume 40264746765](https://github.com/lly8666/wbd-next/actions/runs/40264746765), [S2C one-way quiet+resume 40264755348](https://github.com/lly8666/wbd-next/actions/runs/40264755348), [nonfragmented 1370B application UDP near 1398B observed TUN MTU edge 40264760875](https://github.com/lly8666/wbd-next/actions/runs/40264760875). All **PASS_SCOPED**, real traffic fully injected/delivered active/resumed, quiet phase true 0 injected/received and probe_hz0; null quiet p99 is correct. Both endpoints M4 native `repair_enabled=0`, actual outer DATA retransmits0; all positive Game fixed6 parity planned=copied=sent, expired/failed/codec/capacity0, Stop drained. Active/resumed p99 ~77–78ms. Readback single-way passive endpoint still had 2264/2274 *genuine first* lane copies to carry reverse TUN TCP ACK/FEC; this is not outer retransmission. MTU experiment **does not qualify continuous 10ms cross-HOL** at sparse 1Mbps. Dual direction quiet-tail host CPU PSI spike38.49%; CPU results unusable for gain, capacity_stop remains in force. No forced final-row-loss-at-silence or Game4 quiet tail attestations; do not overstate.

**W110 shared CLI protection:** [Normal fixed2 clean real 40264926353](https://github.com/lly8666/wbd-next/actions/runs/40264926353) **PASS_SCOPED** on same immutable original Rust/Go binary: 1Mbps both directions 96% UDP+genuine TCP 75ms, all delivered p99≤75.7ms, two sides native `fixed requested=applied=1 profile2 pending=false`, outer M2 repair_enabled0, frozen DATA retransmitted0, M2 shadow/retry candidates0 and Stop drained. CPU0.61/0.62s, host PSI0; not a same-VM A/B. This is a regression guard, **not** a fresh Normal Auto under loss certification.

The cumulative W98–W110 representative real Linux scope covers Game OFF and fixed0..6 configuration, fixed6 actual network loss and lane-blackhole FEC recovery with outer DATA OFF, both directions, one-way, quiet tail and nonfragmented near-MTU, plus isolated Normal fixed2 regression. Existing W102 long shared correlated GE residual **~2.43–2.56%** remains above 1%, so scope is not universal high-loss qualification; original W102 host pressure and current W109 PSI peaks disallow heavier runs. Windows/physical and a deliberately damaged last FEC block at exact idle boundary remain NOT_RUN. `capacity_stop=true`, `merge_ready=false`. Evidence `docs/evidence/fec-network-work/20261026-W106-Game2-Game4-fixed0-off-outerDATAoff-clean-PASS.json`, `docs/evidence/fec-network-work/20261026-W109-Game2-fixed6-outeroff-quiet-oneway-MTU-PASS-SCOPED.json`, `docs/evidence/fec-network-work/20261026-W110-Normal-fixed2-outeroff-clean-regression-PASS.json`.
