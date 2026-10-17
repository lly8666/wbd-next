# M0 PACK-009 — 2026-10-17 完整并行包的后续授权

## 权威与实际基线
用户2026-10-17授权完整包并行，覆盖旧024结束后才分配的顺序限制。控制面 main 原HEAD `0275bd184eee65003c621200259f898851e4cb2b`，registry revision2、epoch1；M0任务仍 `R1-M0-HOTPATH-COST-024` PARTIAL。正式权限与路径保持main registry，不按worker分支cursor旧next_action否决新分配，也不回滚旧证据。

检查本轮worker精确远端HEAD：M1 `9d4f68aab2bb1f57bfb96dd8a472bc7eec43f556`（012 CODE `a39ff711fd1f1c505b60b19bfcc7604cdd861aa2`、worker native39015538871）；M2 `c345061c992c505c92eb19181de96a531cc39d96`（009 CODE `6124ce1012e69a2003bdffdc179a774e21096bc3`、native39006207281）；M3 `d5a26ad2bb194af9d83b22d894f6a0e7723870dc`（016 CODE `422a26127496560c0a52e6745ecc8f354e3f4f18`、native default39014567195）；M4 `a48c53f6230ca6bad1259faa24e4e00deec397e0`（013 CODE `b7bcde7dde64633532cae99460eb00855a2e119a`）。各checkpoint→HEAD只有对应cursor-only H，内容未扩大worker authority。M0自身checkpoint `287c092ed39bb7e32c54c17136cff44e5674c5e6`→HEAD只有H119 cursor路径，交接CLEAN而非产品PASS；M0 open_requests为空。主线0275 push Governance39021345566 SUCCESS仅身份/结构。

**复用而不重派**：M3现有完整 `R1-M3-RECORD-LINK-FEC-WORKPACK-016` 仍PARTIAL，继续05/06/07、C01–C04/L01–L04/F01–F06；主线已有`m0-m3-isal-native.yml`可精确固定worker CODE的编译/运行入口，但其native feature与同VM性能结论待实际SOURCE Actions收据，不能靠默认113项通过声明完成。M4 `R1-M4-LEASED-KERNEL-MULTIMSG-WORKPACK-013` 已ready、保留正式分配且作为**必要平台合作冻结来源**：native Linux 94/94组件通过，raw/TUN原生产接线、32条已ready同一次syscall、受保护Go资格仍未通过；由M0消费已交付接口并汇报真实不兼容，不再给M4无新缺口的重复开发包。M0继续engine/Go组合；平台任何新修复仍由M4唯一作者，需真实跨模块阻塞时明确一次最小补丁，不同时争写。

## 新授完整包 M1 · R4-M1-GAME-SHARED-PIPELINE-WORKPACK-013
为什么现在做：012真实rtrb方向transport已交付，M0原Go hotpath方向接线正推进；Game公共组件可以与engine接线并行，但不能抢写原directional和wake修复。

精确基线：上述M1 branch HEAD/H，冻结012 CODE；共享类型以当前main `00-CONTRACTS`的TunnelKey/LaneKey/LogicalPacketId/BufferOrigin/FrozenRecord及M1-012 `split_tx/split_rx` 签名为准，不追别的工位浮动HEAD。施工仅 `09-PIPELINE-GAME.md`、`02-RUNTIME.md`及必要`03-MEMORY.md`，反例G01–G04、R01–R04、M01–M04，受影响C01–C04交M3/M0真实组合。

允许文件：registry原有`crates/wbd-engine/src/runtime/`、`memory/`、`tests/`及M1 logs/evidence/cursor/requests；本包**禁止修改**已有稳定`runtime/directional.rs`、`directional_rtrb.rs`、`directional_compat.rs`、`wake.rs`（若确需签名变动请求M0统一处理），也不得碰`v4_embedded_go.rs`、`v4_owner_crypto.rs`、Go/TLS、wbd-codec/recovery/platform、root Cargo/CI。实现有界共享logical TX job与RX首次交付/去重、每lane单独seal-ready信息、ActiveLaneSnapshot/正常轮换单lane首发、slow lane独立，FEC parity首发按实际wire service，不占repair 10%账本；不给尚未认证的lane伪造资格。不得另造认证、AEAD、FEC encoder或游戏产品capability。

验证/整包done_when：已有native worker功能入口编译一次测试G01–G04、慢lane/Normal旋转不复制、同epoch跨lane互补/24到达顺序、共享ID去重、旧MSS→新MSS、0/1/32/33 ready、Stop/旧loan/失败Wake后再试、parity持续fresh占比/pressure和内存有界。单元/纯公共组件同SOURCE/actions批量，适用性能才单场景同job AB/BA；缺真实Go admission/codec/driver、产品及跨平台标NOT_RUN。冻结兼容M0组装的接口及最小调用示例，整包交付才ready_for_integration；包内自行实现/测/修不逐步骤找M0合并。

## 新授完整包 M2 · R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010
为什么现在做：009 shadow/receipt/RACK/PTO与预算已完整交付，下一真实Go V4接线需要可审计的最小typed事件和send outcome边界；不重造独立恢复引擎。

精确基线：上述M2 branch HEAD/H及009 CODE `6124ce1012e69a2003bdffdc179a774e21096bc3`，使用00的LaneKey/PN/FrozenRecord/TxBatchOutcome身份语义，施工`08-RECOVERY.md`依赖00，A01–A06/R01–R04。只准registry内`crates/wbd-recovery/`及M2日志/证据/cursor/requests；排除engine/Go/codec/platform/共享CI/Cargo和自写TLS认证。适配**已经认证的**lane receipt页、report_seq、旧epoch、冻结handle、prefix/uncertain结算到009状态机；给M0明确预条件、no-capacity返回值和Stop/late-loan，不允许把外观TCP ACK冒充receipt或同cipher重seal。保留稀疏免比例限制（有绝对界）、健康约10%按实际提交wire字节、至多两次修复和fresh无HOL。

验证/整包done_when：用现有Actions native一次编译批量测gap、跳PN/bitmap页、反馈双丢、32bit serial旧报告、RACK/PTO第二次证据、repeat和partial/unknown、generation/Stop、10k/100k fake clock及预算压力受影响子集；只给**新增adapter同SOURCE** PASS，009旧PASS原证据保留，不机械重跑已等价断言。交付输入/输出签名、资源界、回退方式及Go/engine/M3/M4真实接线NOT_RUN；M0才将可信Go身份传给该adapter并进行组合验证。

## M0继续024的准确范围
无需等其他worker。原Go受保护TLS→Rust原AEAD/PN owner→Linux raw/TUN已证持续Normal/off 10Mbps各向；P10固定Rust A `42744982` vs B `8d41c6ff`在run39020675956 AB和39020694554 BA同job分别CPU +0.95%/-2.26%，**INCONCLUSIVE**。旧 D10 full ptrace容量FAIL保留；当前真正缺口是原同session TX/RX共用`Mutex<Entry>`、32 ready非真正同syscall、后续资格023/超MTU。M0只改自身engine/Go/共享入口，M4底层单作者；功能回归批跑，P10/BA/SPARSE/D10每Action单场景，预编译产物复用，受宿主容量限制则停止更重压。按TEST_PLAN §4将seq32回绕、MTU途变、Normal/Game、parity/repair和Wake重新唤醒归入对应既有ID，不重开完成批次。production features0、产品/physical NOT_RUN，不因本登记开放capability。S与cursor-only H分开，推后回读远端。
