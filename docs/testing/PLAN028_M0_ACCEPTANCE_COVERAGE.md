# PLAN028｜M0 当前功能、正式入口与集成覆盖（2026-11-11）


## H1649 GUI原生FEC简化｜正式Windows2025 VM H1648已354项全场通过，新补按钮待本轮结果

H1648 [WinForms 真实 VM Action43160679063](https://github.com/lly8666/wbd-next/actions/runs/43160679063) **SUCCESS**，正式source `d32ac61ddffbd14acc0b07afc895dc26abe8d295`（原Go donor `a7a82db...` 装配、Rust DLL SOURCE8a、**新Go EXE SHA256 `edbb9715f19547dadc2117b2d2fe39169762480de3244c639ecbb0c1a777f582`**）；原ZIP artifact13917194780 SHA256 `cf53c2b5bd2297a9c51fc4699c98c2bfd71d0c1f30116be959b918b3382792e3` CRC全5成员验证。原Windows VM编译、49项可见配置各自GUI保存/真实原Go V4 `--check-config` 读回、源锁 **七原生模式＋7强度×Normal/Game2/Game4共21组合**、三AEAD、非法值/旧模式拒绝、WAL安全和WinForms按钮（FakeSession）合计 **354条检查PASS**。旧H1647 Action43160277750因测试fixture C# `using` 作用域报错FAIL原样保留。H1648治理43160679121全PASS，旧失败不改写。

按用户**不需旧项目兼容**，唯一可见FEC模型：**关闭（产品默认）／固定强度／仅Normal自动**；固定七档源于Rust比例 `r/k = 1/8,1/4,3/8,1/2,3/4,1,5/4`（按块进位和MAX_R封顶，非总体线速占比或成功保证）；不再展示旧Go `fec-mode/fec-parity/fec-min-parity/fec-start-parity` 四重复旋钮，其真实冷建链受保护载体仍由当前V4字段自动推导：Normal Fixed6需`fixed/parity4`，其他`off/parity0`。对Game Auto警告且只读验证拒绝，**不静默切换模式**；FEC Fixed/Auto只读状态是 `pending_native_auth`，**绝非真实 Rust/OS Applied**。截图确认Off时固定/自动区域折叠，避免两套设置混乱。

H1649另收少数可安全执行的VM按钮：导出后导入JSON的实际MainForm路径、只读磁盘状态和原生WFP预检的实际点击、独立固定/自动界面图，以及主标签改为“丢包纠错 FEC”。真实 GUI 经点击连接后签名Npcap/Wintun、外部Npcap下载/Explorer/ChinaIP联网更新和file-picker人工文件选择仍明确区分为**NOT_RUN**（无外部环境不测），不得把模拟会话与实体Wintun相混。七模式真正受损原生Windows业务继续按SOURCE8a旧Go独立Action记PASS_SCOPED，**新GUI Go哈希不直接继承旧网络验收**。028 IN_PROGRESS；不扩大029/030。

## H1645 Windows GUI 53项和七模式实际VM已有251步；显式AES冷路径接线待新源复验

[H1644 Windows2025实际GUI编译/配置 Action43153401230](https://github.com/lly8666/wbd-next/actions/runs/43153401230) 整体 **FAIL** 原样保留；正式WinForms与新original-Go V4 EXE均真实编译，新Go单文件 SHA `f9996e5bddebba015646b54f88d8a25fe9366c64686bebee53ab063abfc58553`（该次测试源码3caf5b70，不是旧H1600 Go hash）、Rust ISA-L DLL原SHA `7c8ddd808d08cfa18cf431fd5945d6c705bddaa6dd19a94e1891170ffa91d37d`。保留原始GUI JSON receipt artifact13914906742：**251条逐项检查成功**，包括53字段的编辑→保存→真实原Go CLI `--check-config` 有效值回读、七个V4合法模式和非法模式、FEC Fixed/Auto pending-not-Applied、ChaCha；实际在 AES128-GCM 且旧carrier `fec-mode=legacy` 时拒绝 `realityfront: invalid admission parameters`，故**GUI三AEAD整体尚未通过**，按钮后续阶段未执行，不能以251局部PASS替代全场。确认原因是旧Go V3保护层明确拒绝 legacy+非ChaCha，而旧GUI默认 legacy 实际表示FEC Off。H1645仅对 `--native-v4-product=true && legacy && parity=0 && AES显式` 使用相同原Go认证 **off** carrier，配置读回新增 `effective-original-carrier-fec-mode=off`，不更换cipher或FEC、不改变历史V3和不支持组合。等待新SOURCE正式组装Go+WinForms真实VM结果；**新Go冷认证源码已改变，不能复用旧SOURCE8a网络AES结果当本源码验收**。独立真正GUI点击后签名Wintun起网仍须另一真实网络场景；FakeSession的按钮验收只限UI事件。

H1644治理与maintenance 原FAIL原因是新五客户端证据缺 `source_sha` 顶层字段（原本正确的product_source_sha已经存在）；H1645补原正式SOURCE8a，保留原失败Action和原报告，不变验证阈值。五客户端H1643真实原始离线复判成功资格与七模式历史SOURCE证据无变化。

## H1644 原始五客户端180秒严格复判完成；Windows GUI 当前编译接续（2026-11-12）

**五客户端当期SOURCE** `8a31375e36bb6a93860c5579e64b4a39d0b6e346`；原始单一真实原Go TLS/Rust ISA-L Linux x86 kernel/netns业务 [Action43148997176](https://github.com/lly8666/wbd-next/actions/runs/43148997176) 仍 **FAIL**（旧报表不识别服务端B代已认证M4提交）。原始ZIP13912204248及report/server/cpu/qdisc各SHA保留。[H1643严格离线复判 Action43152631016](https://github.com/lly8666/wbd-next/actions/runs/43152631016) **SUCCESS**：对原始ZIP八项SHA匹配、四组缺/错/重放负例、六个真正服务端B端口的5环节M4/Health/OS接管顺序和五端旧代精确Stop逐项核验，不重跑180秒网络，`rotation_verdict=PASS_ALL_FIVE_SCOPED`，`alerts=0`。五客户端真实送出**1,716,864 UDP**、首次唯一收到**1,714,925（99.8871%）**，真实未到**1,939**；Alice/Bob原双向TCP每向帧43317/43317。内核真实损伤各客户端0/1/5/15/**30%**，单程0/15/50/100/**250ms**，**仅Erin**最高，不能称五端全为30%/250ms；其他四端outer1460，Erin显式outer1280；跑的是30/60/30/50s有界容量阶梯，非600s高压/Windows独立DUT L3。原服务器CPU平均单核54.478%，峰RSS127052KiB，仍未得失包包含的一向p99；详细 [H1644结构化原证据](../evidence/M0/PLAN028-H1644-ORIGINAL-H1642-FIVE-NATIVE-180S-STRICT-M4-OFFLINE-PASS-20261112.json)。原Action失败与旧报表保留，结果只能记 **PASS_SCOPED_OFFLINE_REJUDGED**。

**GUI 当前正式装配原生问题与待验：**本批修复旧V4 `--check-config` 对已支持的Fixed/Auto误报 `fec.status=rejected`、导致GUI误挡连接的实际缺口；源锁Go新 `fec.status=pending_native_auth`（`fec.applied_profile=unknown`）只代表通过配置校验，**绝非认证/OS Applied**。原生GUI不再提供3 lane，Game Auto/旧V3 legacy auto明确拒绝，Normal最高Fixed6需原Go冷carrier fixed4；默认仍Off、outer1460、outer-repair on。GUI真实Windows2025 VM [Action43152631015](https://github.com/lly8666/wbd-next/actions/runs/43152631015) 最新整体**FAIL**：正式装配和新原Go EXE/WinForms编译成功，字段自检中旧测试fixture仍含16B route-key，被原生V4正确拒绝（原始FAIL保留），**按钮尚未执行**。H1644将两处fixture都真正装入最终manifest 32B，并加构建前源字节校验，新GUI独立Action结果待收。即使VM按钮通过，真实GUI发起的签名OS/Wintun会话仍独立NOT_RUN。

**治理：**H1643 [Action43152630949](https://github.com/lly8666/wbd-next/actions/runs/43152630949) 原FAIL：热文件总32839超过32768 **71B**，本批仅缩短M0 cursor而不放宽预算；需本批治理Action重新通过。用户排除/缺环境的独立Windows A/B/C 1800s、近innerMTU、多Wintun维持NOT_RUN；029/030不进入。

## H1639 Windows 七模式正式SOURCE8a 每模式真实原生独立场已齐（2026-11-12）

**正式二进制SOURCE** `8a31375e36bb6a93860c5579e64b4a39d0b6e346`（H1600 build43027983611），Windows签名Npcap/Wintun＋Ubuntu WSL2 Linux 原Go标准TLS443/Rust原生业务；每个独立Action真实30% loss／单程250ms、双向各10Mbps、60秒，外层1460、最终双向TCP/UDP和owned Stop，原始ZIP/37项CRC和单文件Go SHA核对。H1637其余三场：

| 模式 | Windows首次交付 | Linux首次交付 | 精确native Action/原ZIP SHA256 | 限制 |
|---|---:|---:|---|---|
| Normal Fixed6最高 | **99.9728%** | **99.9280%** | [43145185794](https://github.com/lly8666/wbd-next/actions/runs/43145185794) **SUCCESS** `c292572edeba8db409301290c448fa99fbaa6f85ff2306908983767d9bfc6a4b` | Linux Fixed6 installed=true，Windows Rust mode=fec-fixed；Win端固定档单独installed bool本场未打点，不冒认 |
| Game2 Off | **90.9529%** | **90.9705%** | [43145182267](https://github.com/lly8666/wbd-next/actions/runs/43145182267) **SUCCESS** `27f86b6e1fe15ef84df11c2d6b59fb1a0c836a09e74dbcf6d8bd51c3d3deba8c` | 两lane Off和真实残损，不是近全交付保证 |
| Game4 Off | **99.1598%** | **99.1571%** | [43145187468](https://github.com/lly8666/wbd-next/actions/runs/43145187468) **SUCCESS** `d4eff024f19a8f116ede75f045e228df86579f4a90810a78e343a9293ba69c39` | 四lane Off下真实剩余损失，不是固定FEC |

源锁原始report和每进程CPU/RSS详情 [H1639 evidence](../evidence/M0/PLAN028-H1639-SOURCE8A-WIN-THREE-REMAINING-MODES-SIGNED-REAL-LOSS30-20261112.json)。连同之前Normal Off/Auto、Game2/4 Fixed6，**Win七模式各一短真实业务代表场PASS_SCOPED，Linux x86亦七场**，不是同源Win五端满压、1800s独立DUT或全设置排列验证。CPU不同VM不得用于因果比较；单向/失败包完整p99未测。

**GUI资格按层分账：**正式组装清单outer1460和FEC Off已确认，旧Go donor1500不代表产品。H1638补齐正式GUI漏映射的 `outer-repair=on/off`（默认on），新增真实编译WinForms全字段check-config和按钮点击VM工作流；第一次 [GUI Action43147117898](https://github.com/lly8666/wbd-next/actions/runs/43147117898)在正式装配PASS后、UI执行前Python CP1252读取中文UTF8失败：原Action **FAIL/HARNESS_FAILURE**、GUI本次仍NOT_RUN。H1639精准改UTF-8后另派；即使UI模拟session事件PASS，也不能当GUI真实签名Wintun/OS端到端连接PASS。不可用A/B/C独立长测、用户跳过的近innerMTU及多Wintun仍保持NOT_RUN。

## H1636 当前SOURCE8a签名Windows Game2/Game4 固定最高FEC6双场同时完成

两项独立的 [Game2 FEC6 Action43139768028](https://github.com/lly8666/wbd-next/actions/runs/43139768028)、[Game4 FEC6 Action43139771735](https://github.com/lly8666/wbd-next/actions/runs/43139771735) **均整体SUCCESS**，各自签名Windows2025 Npcap/Wintun＋Linux WSL2原Go标准TLS443／Rust M4真实内核UDP/TCP，60秒双向各10Mbps、每向真实tc30%丢包／单程250ms、outer1460／inner1358、两端各自Stop。保留两个原始ZIP，CRC均无误，来源为正式产品构件SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346`，独立 [H1636证据](../evidence/M0/PLAN028-H1636-SOURCE8A-WINDOWS-GAME2-GAME4-FEC6-LOSS30-250-PASS-20261112.json)。

| 完整本机原生场 | Windows真实first | Linux真实first | 原Rust服务端FEC回执和内核loss | Windows原Go+Rust进程资源 |
|---|---:|---:|---|---|
| Game2 Fixed6 | 100.0000%（73640/73640） | 99.9823%（73610/73623；未到13） | `GAME_FEC_APPLIED lanes=2 fixed profile=6`，FEC`recovered_candidate=6778`，eth0/ifb drops105196/102266 | 76采样77.078s，CPU7.1406s/单核9.264%，峰值RSS58.48MB |
| Game4 Fixed6 | 100.0000%（73640/73640） | 99.8778%（73532/73622；未到90） | `GAME_FEC_APPLIED lanes=4 fixed profile=6`，FEC`recovered_candidate=585`，eth0/ifb drops208661/146714 | 76采样77.984s，CPU33.4062s/单核42.837%，峰值RSS73.02MB |

两场业务真实成功，不表示 FEC`recovered_candidate`可与业务唯一交付直接相加；Linux方向未收到的13/90包保持真实损失，成功报文RTT p99 531–625ms不含未返回探针，也不是校准过的一向p99。不同托管VM的CPU数据不得用于归因或单机A/B；旧owner限制不变。加上当期 [Normal Off Action43136758689](https://github.com/lly8666/wbd-next/actions/runs/43136758689) 和 [Normal Auto Action43138301038](https://github.com/lly8666/wbd-next/actions/runs/43138301038)，**当前SOURCE Windows 30%/250ms四个独立代表场均有真实产品原生结果**，但并非 Windows七模式全组合/五客户端满载/独立1800秒DUT或人手GUI已收口。Windows Normal Fixed6/Game2 Off/Game4 Off当前SOURCE损伤代表场仍未跑。缺独立A/B/C环境1800s不派，用户已排除近innerMTU/同一Windows多Wintun。

## H1632 Windows签名真实30%/250ms短场（Normal Off）已完成；显式Auto下一独立场待原始结果

**当前产品二进制SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346`**，测试源码 `12d2c2378846ee34737a5f38555533d98c13cbbc`，单签名Windows Npcap/Wintun→真实Ubuntu WSL2共享Linux Go/Rust，独立[Action43136758689](https://github.com/lly8666/wbd-next/actions/runs/43136758689)整场native job **SUCCESS**，原ZIP artifact13907294714 SHA `59ca2be8ad7d08a429726e52bfc8c7bbe735818ba3b5e2f2be77e62b8902493c`、37文件CRC/原报表SHA核实；[全部原始数字和限制](../evidence/M0/PLAN028-H1632-SOURCE8A-SIGNED-WIN-LINUX-30PCT250-NORMAL-OFF-20261112.json)。

真正双向tc30%/单程250ms/每向10Mbps/60s、小包64/128至1200B，双侧真内核每向发99,551：Windows首次收到Linux **71,958（72.2825%，7.2147Mbps）**、Linux首次收到Windows **71,974（72.2986%，7.2087Mbps）**，各有**27,593/27,577未交付**，实际ifb/eth0内核drops33,651/33,718，invalid0 duplicate0。源锁标准TLS、Rust M4、真UDP/TCP、outer repair**on**、FEC **Off（仍是默认）**，Windows/Linux OS内层MTU1389及双方owned Stop、Npcap cleanup均通过，**功能/资源PASS_SCOPED，绝非高损“可靠交付”PASS**。Windows Go+Rust原进程样本74个，74.672s CPU累计1.9375s、单核均值2.595%、工作集峰43.95MB；应用单向p99/失败包逾期与全队列年龄未测；成功包间隔45/234ms不能替代失败包p99。尚非五客户端150/600s高损容量或独立DUT 1800s L3。

H1632单独将FEC **Auto显式**选中，同一业务量/包型、损伤等级、outer1460/正式SOURCE8a重用，创建 **另一个 Action**，在其真实Report/Stop结束前标 **NOT_RUN/PENDING**，只用于该受影响入口是否有效、自适应FEC首次交付和处理代价，**不同VM不得算CPU对照**。无独立A/B/C环境的Windows L3、此前用户跳过的近innerMTU与同宿主双Wintun仍不测；029/030不扩展。

## H1631 当期 Linux x86 七模式补缺已全部完成（2026-11-12）

**产品二进制SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346`，原Go TLS443＋Rust ISA-L共享TUN真实Linux x86 kernel；没有重编译。**此前H1621静态审计列出的三个**当期SOURCE**单项实网缺项，已经由三个独立Action真实结束并校验原ZIP/CRC及完整3个ELF hash；新[H1631源锁证据](../evidence/M0/PLAN028-H1631-SOURCE8A-CURRENT-X86-SEVENMODE-GAPS-PASS-20261112.json)。历史第一/二次夹具FAIL原始Action仍保留，不改写。

| 缺项模式 | 原始Native Action/ZIP SHA256 | 原 OS/TLS/Rust/真实业务及退出资格 | 未推论范围 |
|---|---|---|---|
| Normal Fixed6 最高 | [43135302816](https://github.com/lly8666/wbd-next/actions/runs/43135302816) **SUCCESS**，`f4da52397f9159438bae97be550dd63e2241cf612d0126ffef3b7e9dc9e1d44e` | 真实fixed6 Rust读回、自动/32、源IPv4 `.4→.9→.4`、物理1500→1280→1500、OS inner1375→1195、世代1→2→3旧代各精确Stop，Game4兄弟**80/80**真UDP持续、Normal新代**16/16** UDP、全部shared TUN Stop：**PASS_SCOPED** | 不是Windows/30%高损/单向p99 |
| Game2 Fixed6 最高 | [43133373054](https://github.com/lly8666/wbd-next/actions/runs/43133373054) **SUCCESS**，`b5499e8ae4c1078a73745056988429a96459105fac7947d42d50db2aed64f211` | 两lane原TLS/Rust、源 `.2→.9→.2` 物理MTU变化、inner1358→1178，三世代旧代精确Stop、Game4/Normal兄弟各窗口真UDP**80/80**，Game2新代**16/16**真UDP与最终Stop：**PASS_SCOPED** | 不是Windows当前-source FEC2或全性能压测 |
| Game4 Off | [43135302756](https://github.com/lly8666/wbd-next/actions/runs/43135302756) **SUCCESS**，`52d117688209e475ced0c916b8a78c70fc03814dc8050a181fa82abf10f0934d` | 四lane FEC实际Off、源 `.3→.9→.3`、inner1373→1193、世代1→2→3/Stop，Normal兄弟首/次切 **48/80**真UDP，Game4换代**32/16**真UDP、各own Stop：**PASS_SCOPED** | 非Windows L3或近内层MTU数据包 |

其余四模式当前SOURCE已有可复用证据：Normal Off/Auto、Game2 Off、Game4 Fixed6；**七模式按原生Linux x86代表场分账已覆盖，而不是每模每平台全新300s/1800s矩阵。**既定默认outer1460/FEC Off/ChaCha/outer-repair on/Linux rotate0/Win 15/90/idle0不改。独立Windows A控制/B DUT/C外部Linux长测**INFRA_BLOCKED**不派；near-derived-innerMTU和同Windows宿主双Wintun用户已跳过且旧FAIL保留。

**另行独立一场 Windows签名Npcap/Wintun＋真实Linux S8a 10Mbps双向、30% loss/250ms单程、60秒正式业务**以H1631 wrapper新建精确outer1460场景、复用H1600成功构件；其最终目标Action仍须取原始严格报告/第一失败/Stop才可记PASS，触发/包装不算Windows网络已通过。该短场不替代五客户端600s容量或独立DUT L3。

## H1626 2026-11-12 CURRENT main source-locked coverage (replaces stale unverified labels below)

Formal original Go TLS443 + Rust ISA-L product binary SOURCE: 8a31375e36bb6a93860c5579e64b4a39d0b6e346, build Action 43027983611; this evidence/handoff correction is based on main HEAD 60006d13ece22506c4ef9ae930270b5a4fa173aa, which is NOT a newly built product binary. No product, default or native test changed. Prior unsuccessful Actions are retained.

| 功能 | 平台 | 正式入口 / 默认 | 精确SOURCE | 业务与配置读回证据 | 范围/限制 |
|---|---|---|---|---|---|
| 标准TLS、同账号独立安装、五客户端生命周期 | Windows2025 signed single Npcap/Wintun + four Linux x86 TUN + shared server | Win CLI native-v4-product **true** by default, GUI same exe, Normal one lane / FEC Off | 8a31375e36bb6a93860c5579e64b4a39d0b6e346 | [H1601](../evidence/M0/PLAN028-H1601-SOURCE8A313-H1596-WIN-LINUX-SAMEACCOUNT-150S-20261111.json) Action43027983611: Win Alice and Linux Bob same login separate Installation IDs and auto /32, real 150s UDP first unique636494 TCP1458 valid, Win owned Stop then Bob4 new real UDP, all six Stop, WAL/WSL cleanup | **PASS_SCOPED 150s**, not 600s/1800s |
| 自动/手动IP、三套AEAD | Win x64 single Wintun, Linux x86/ARM historical | empty lease4 auto, manual explicit /32; ChaCha20-Poly1305 default, AES128/256 explicit | 8a31375e36bb6a93860c5579e64b4a39d0b6e346 auto AES256/heterogeneous peers; fd4732ec4adffa442a0bc25a145ed6ea1d1259a8 manual | H1601: Win OS 10.66.0.203/32 Rust cipher3, Bob OS10.66.0.130/32, Linux ChaCha/AES128/AES256; [H1592](../evidence/M0/PLAN028-H1592-SOURCEFD473-WIN30-COLD-TLS-PASS-SCOPED-20261111.json) Windows manual /32 | **PASS_SCOPED** independently selected ciphers cross-OS; every Windows cipher/mode permutation NOT_RUN |
| 七模式/lanes/FEC | Windows/Linux x86 and ARM historical | Normal-Off; fixed highest and Normal-Auto explicit; Game2/4 default Off, fixed6 explicit; Game Auto unsupported | old 0cda91575d171c1f8141e937aac91c39d6b303fc versus current 8a31375e36bb6a93860c5579e64b4a39d0b6e346 | [H1621 source audit](../evidence/M0/PLAN028-H1621-SEVENMODE-DEFAULTS-SOURCE-AUDIT-20261112.json): old Action41970545107 7 scenes; current H1604 Normal fixed representative, H1613 Auto, H1617 Game2Off, H1609 Game4 fixed6 | **Old seven PASS_SCOPED only**; current Normal highestFixed6, Game2Fixed6, Game4Off and full Win seven underqualified |
| MTU/outer repair/FEC backend | Win signed + Linux x86 / ARM build | complete outer IPv4 MTU **1460** default, explicit max1500; Rust derived inner; outer-repair on default; native ISA-L pinned build | 8a31375e36bb6a93860c5579e64b4a39d0b6e346 | [H1623](../evidence/M0/PLAN028-H1623-SOURCE0577-WINDOWS-SIGNED-IDLE105-PREBUILT-TWO-OS-NATIVE-20261112.json) Win and Linux OS inner1389; [H1609](../evidence/M0/PLAN028-H1609-SOURCE196D-PARALLEL-PREBUILT-NORMAL-GAME4-PATH-20261111.json) path1280→inner1209 Normal or1178 Game4Fixed6 | **PASS_SCOPED** OS readback; near-derived MTU actual Win payload NOT_RUN, ARM64 accelerated build != all-mode runtime |
| A→A+B→B/candidate failure and Game siblings | Linux x86 native; Win live sibling | Linux rotation-interval default0, Windows rotate0; explicit timers | 8a31375e36bb6a93860c5579e64b4a39d0b6e346 | [H1604](../evidence/M0/PLAN028-H1604-SOURCE8A313-REAL-A-B-GAME-LANE-ROTATION-20261111.json) Game2 A+B group and Game4 unchanged siblings; [H1617](../evidence/M0/PLAN028-H1617-SOURCECF03-PREBUILT-NORMAL-FAILED-B-A-LIVE-GAME2-OFF-20261112.json) Action43062378203 failed B2 keeps healthy A true kernel UDP then B3 success, Action43061710360 Game2 two lanes | **PASS_SCOPED** Linux, not Win AutoIP physical path |
| keepalive/dead/idle true wake | Windows signed manual IPv4 + Ubuntu WSL2 and Linux x86 separate | Win 15s keepalive / 90s dead / idle0 **disabled by default**, Linux according to platform | 8a31375e36bb6a93860c5579e64b4a39d0b6e346, H1623 harness 0577bb29844375535b0a79955d49e409df604b55 | [H1623](../evidence/M0/PLAN028-H1623-SOURCE0577-WINDOWS-SIGNED-IDLE105-PREBUILT-TWO-OS-NATIVE-20261112.json) Action43110135433 108.48s no business → 60s duplex 10Mbps each, original UDP Win99497/Linux99551 all first arrived, real TCP, Stop; [H1613](../evidence/M0/PLAN028-H1613-IDLE100-DEAD106-PREBUILT-X86-NATIVE-SCOPED-20261111.json) Linux idle/dead/reauth | **PASS_SCOPED**; separate Win Health count, Win dead106/AutoIP/path NOT_RUN |
| 压力/CPU/RSS/p99 | Win hosted, Linux x86/ARM historical | pace0.7 is test fixture, **not** product default | 8a31375e36bb6a93860c5579e64b4a39d0b6e346 Win150s; old Linux ed965f2dd93bc5520d9a17f211ff39029d4d6594 | H1601 Win **outer both-directions TOTAL** median108.834Mbps, host CPU busy max52.7%; older Win1.0x test CPU max92.6%, old Linux 304Mbps outer duplex combined | **NOT_FULLY_QUALIFIED** new source Win 30%/250ms 5-client sustained, one-way failure-aware p99, per-process CPU/RSS, queue-age, controlled L3 |
| independent Windows 1800s L3 | A separate controller, B non-runner Win signed DUT, C independent Linux server/client | same original product, not special test-only fallback | 8a31375e36bb6a93860c5579e64b4a39d0b6e346 binary reusable but no qualifying new L3 | [L3 isolation hard gate](PLAN028_L3_ISOLATED_CONTROL_PLANE.md): hosted Windows Runner+WSL2 self-coupled network/control-plane; no available A/B/C independent rig | **INFRA_BLOCKED NOT_QUALIFIED**; do not repeat hosted 1800s and call PASS |
| history / excluded | Win two independent Wintuns same host, Android, physical, 029/030 | two Wintuns user excluded, WAL route CAS intact | old c3e60772c2f99e5d7fa1cadb0284b3e1addca1d4 and H1587 3b6d53c30531f6820c220f9e6c23f8a23480227c | original Action42979705842 150s local UDP/TCP succeeded but shared echo exited before full test final oracle (whole Action **FAIL**); original governance42979705889 FAIL; same-Windows dual Wintun43001721886 FAIL; newer 43027983611 PASS_SCOPED and H1625 governance 43113485314 / maintenance 43113485414 SUCCESS | Never override historical FAIL or claim complete. Android/public WAN/029/030 OOS |

Formal SOURCE 8a31375e36bb6a93860c5579e64b4a39d0b6e346 per-file hashes from original H1601 evidence: Windows original-Go EXE 63b4a24abb0e7c775be5e58d3e54036f4bfab0491bc992a0147b8fe57886cd7c, Win Rust DLL 7c8ddd808d08cfa18cf431fd5945d6c705bddaa6dd19a94e1891170ffa91d37d; Linux x86 client 7f347ae9dc878edf508aa5fdeb8668ccae653682d01898435b69d42c94a555d1, server 9188f3941eba3dfd48831f779e0d8b73d3b31deda4c1978a1f270e11d75dcc71, Rust SO 2947d148d325e198acd920c56803ad168175ba11590396478682693fcf5922dc, original Go donor a7a82db31fe736ffedee330795a3234d358f1984. ARM64 two accelerator/native build manifests and 11-file overlay scope tracked separately in H1593/H1546 and older original netns evidence, NOT same SHA as x86. Builds, runtime backend, driver OS effect, fresh-product scope cannot be silently conflated.

**状态：IN_PROGRESS，不是收口证明。**此页是接续导航，规范门槛仍以 [PLAN028_INTEGRATION_ACCEPTANCE](PLAN028_INTEGRATION_ACCEPTANCE.md) 为准。功能卡见 [inventory](../features/inventory.json)。旧证据不被新源码重新标记为 PASS；失败 Action 原样保留。历史矩阵仅按所列 SOURCE/平台/场景有效。不得开展 PLAN029 DNS/填充新能力或 PLAN030 服务管理。

## 当前入口、产物与证据规则

- **Linux x86_64 / ARM64：**原始 Go credential TLS443 冷协商、`r0/go_overlay/internal/v4productcli/linux.go` 的当前 CLI、`crates/wbd-engine` Rust M4 和原生 raw/TUN。Windows/Linux 开发源码在 `main`、原始 Go 固定 donor `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`；`r0/go_overlay/assembly/manifest-plan020-m0.json` 固定每一正式替换/新增 Go blob。ARM64 **不**能只凭仓库存在文件：要核正式 H1546 11 文件装配 + 实际后端与 binary receipt。
- **Windows x86_64：**正式 `wbd-client.exe` 默认 `--native-v4-product=true`；WinForms `windows/gui/Portable.cs` 经当前 manifest 组装后显式启动同一 `--native-v4-product --control-stdin --config` 子进程。默认 false 的旧隐含入口已取消，显式关闭不会自动退回旧 V3。正规装配为 `tools/prepare_windows_wiring.py` + `r0/go_overlay/assembly/assemble.py` + manifest；`EXTRA_BRIDGES` 明列 Game group 和原生认证附加桥。Go只负责认证/冷路径，Rust为收发/记录/FEC稳态；签名 Npcap/Wintun/OS WAL 为真实产品硬门。
- **最新实际测试源码：**`8a31375e36bb6a93860c5579e64b4a39d0b6e346`（H1600真实Win+Linux同账号五端150s、源码含H1596唯一Wintun已验；前序的fd473只是30%冷建链），`813e4c5c71fe2a1f2442bfda0ce19c205a398d03` 为最初Windows自动IP/三cipher接线源码、不是最新HEAD。`fd4732ec` Action `43009320538` 实Windows30%冷TLS+M4+签名OS+Stop成功（**仅冷建链**），`43009320436` Linux x86/ARM手动两账号真实TUN/Stop成功，`43009320389` Windows各模式/WAL scoped通过；旧SOURCE `dd82db7e` Action `43000134310` 真实Windows自动AES256+四Linux三cipher150s严格报告PASS_SCOPED（Action整体后置FAIL）。**Windows单宿主双独立Wintun路由H1587仍FAIL；SOURCE `8c0421c3` Action `43014043726` Windows自动AES256/四Linux三AEAD真150s/六owner Stop已PASS_SCOPED，不能写全组合均通过。**
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
| idle / 业务唤醒 | **Windows idle-dormant=0**（不自动休眠） | 显式 `idle-dormant`，真业务刷新payload idle，Health不可刷新 | 双边auth idle→Dormant；真业务 WakeDemand→新TLS/Rust，显式Stop不复活 | 历史Linux100s零业务后新UDP PASS；Windows手动/32真实idle/Wake在H1623 SOURCE8a PASS_SCOPED，Win AutoIP物理path未验 |
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
| Windows自动/手动IP、三AEAD不同终端同服 | Win2025单Wintun + Linux x86/ARM | 默认auto/ChaCha/Normal；手动/三AEAD显式 | 最新`8a31375e` H1601 Action`43027983611` [evidence](../evidence/M0/PLAN028-H1601-SOURCE8A313-H1596-WIN-LINUX-SAMEACCOUNT-150S-20261111.json)，早期`8c0421c3` H1594 Action`43014043726`，`fd4732ec` 30% cold Action`43009320538`，Linux ARM `43009320436` | **真同账号跨OS独立安装双auto/32、三AEAD、五客户端150s UDP/TCP全Stop PASS_SCOPED**；单Windows宿主两Wintun不测且旧H1587 route FAIL保留；Win手动AES128另有旧SOURCE真OS局部证明，非本SOURCE新150s |
| 七模式产品正向 | Windows/Linux x86_64 + ARM64 | Normal Off/max/Auto、Game2 Off/max、Game4 Off/max，FEC默认Off | 旧 `b6b964afa7ffec5795f2c11c6e0620f223e684ac` Action40560287417、旧 `33ed20...`；新的Win编译813 | 老源七模式真实正向可复用非改动组件；Win新源模式/cipher搭配 NOT_RUN |
| A→A+B→B、Game2整组交接、Game4健康兄弟不断 | Linux x86_64与Win共服 | Windows默认rotate0不自动开启；Linux真实测试显式97–127s | `8a31375e` H1604 [原生日志hash/事件](../evidence/M0/PLAN028-H1604-SOURCE8A313-REAL-A-B-GAME-LANE-ROTATION-20261111.json)、H1600 Action`43027983611` | Bob/Erin gen2 authenticated Health后发布+B正常Stop，Carol Game2整组两lane B→A精确退休，Dave Game4仅lane1轮换三兄弟server原生无重启；五端150s真业务无断流 **PASS_SCOPED**，新SOURCE Windows默认rotate0，B失败留A未触发 |
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

## H1596/H1597用户新范围与0.7倍同账号跨OS验证

用户2026-11-11明确不要求跑**同Windows宿主多个Wintun**，H1587第二Wintun全局/1路由+WAL失败作为历史真实FAIL/未支持组合保留，不再派发；**不等于修复、也不把该组合说成PASS**。替代直接验用户承诺同账号多设备：单个真正签名Win2025 Wintun Alice + 独立Linux Bob同原TLS账户、各自原Go安装ID与不同server auto/32，其他三个Linux异构AEAD，同一共享TLS443/Rust服务器；真实150s双向UDP/TCP、Windows退出后Bob仍真实UDP与六owner Stop均须新源严格证据。

H1596 SOURCE`49630902` Action `43024873684`进行时，前置源码回归`43024873825`与治理`43024873618`成功，但离线发现其测试业务pace选择0.6**低于已有真实app的0.65下限**（`tools/m0_plan028_h1548_mixed_os_app.py`）。H1597调为**仅夹具/CI显式0.7**，严格保留发生器有效值界限与六端pace读回，避免此前4vCPU宿主原负载CPU92.6%再撞高压；原H1596 Action结果单独留存，不在它运行中重复派发。H1597尚无真网络结果，**NOT_RUN**。产品默认仍1460/Normal-Off/ChaCha/outer重传on/Linux rotate0/Windows15s-90s-idle0；不能将夹具pace0.7推广成产品全局默认。

## H1598 原始H1596严格失败收据及唯一合法负载复验

SOURCE`496309022f2b1f9d39c1b2d7db80770a49321886` Action [43024873684](https://github.com/lly8666/wbd-next/actions/runs/43024873684) **整体FAIL**，严格报告 `FAIL_OR_NOT_RUN_TRUE_ORIGINAL_OS`，首错 `H1574 native app exited before real 150s server`，网络业务阶段没完成。取回原始artifact`13857197465` ZIP SHA256 `8dd77f2776abf360c5ae5a69698f41ed6948b504ca2c6bd89cbb815d2c752afc`。既有真实业务发生器代码明确只接受`0.65<=scale<=1.35`，该source夹具传入`0.6`，在真实150秒阶段前被拒，是测试参数失败，不是产品丢包、OOM或已验150s。**保留Action原始FAIL。** 但此前Win2025签名Wintun确实自动获得`10.66.0.132/32`/AES256原Rust cipher3，Linux Bob以**同一受保护Alice用户名/口令但另一Go独立安装身份**获得`10.66.0.173/32`真TUN读回，四Linux其他自动/32独立，先导五端内核UDP`40/40`真实回声与Windows客户端Stop、WAL零遗留、WSL bridge/netem清理PASS，这些仅是**早期AUTH/OS/UDP PASS_SCOPED**。原始严格报告SHA256 `7077c9834ac835f575c3c276e8948fbaaf7781dce6181a4c319a3f334486591d`。详细原始状态和二进制见[H1598 evidence](../evidence/M0/PLAN028-H1598-SOURCE496309-SAME-ACCOUNT-EARLY-OS-FAIL-FIXTURE-20261111.json)。

H1597 SOURCE`7f84a518e8fbcc6c9e53a34072bb4ea5923831c2`已把**仅测试夹具**合法负载改为`0.7`（六端实际pace读回必验），并通过治理Action`43025487562`、`43025487403`；旧Action终结后本提交只派 `[plan028-h1596-same-account-win-linux-150s]` **一场单Wintun、四Linux、真150s再验**。新SOURCE结果需事后取artifact，当前`NOT_RUN`，不扩展029/030。

**H1600 workflow语法修正：** H1599 SOURCE`798762d9` GitHub原生工作流在启动前直接失败 Action`43027647645`，原因只有`run-name outer`新增H1596默认1460标签时多一个`)`（13开/14关），**网络完全未运行**；原配置失败保留。H1600修到开闭相等并为正式触发的H1596同账号跨OS150s补源级校验，仍**仅一Windows Wintun**。本源新的最终结果必须看Action原始strict报告，不借旧错配成功。

## H1601 真同账号跨OS一个Wintun、四Linux完整150秒（本源最新）

精确SOURCE `8a31375e36bb6a93860c5579e64b4a39d0b6e346`，Action [43027983611](https://github.com/lly8666/wbd-next/actions/runs/43027983611) overall + native job均SUCCESS。artifact `13861275233` ZIP SHA256 `4a5e88ea353015487a5d2f3249b8b30522d5e3e57fcbd99e76c0cd48df39b61d`，严格报告单文件 SHA256 `cb790d21612e4b99725b93fb3cb983b681c7ae48b16e5473ff0bcbdf4e615fcb`。引用 [H1601详细逐字段证据](../evidence/M0/PLAN028-H1601-SOURCE8A313-H1596-WIN-LINUX-SAMEACCOUNT-150S-20261111.json)，原始log未删。

| 功能/入口/默认 | 精确SOURCE及实际读回 | 资格/限制 |
|---|---|---|
| 正式Windows原Go→Rust M4→签名Wintun、默认auto IP/AES256显式 | `8a31375e` Win Alice `auto lease 10.66.0.203/32`/OS 同值，AES256 Rust ID3、outer1460→Windows inner1389；源锁Windows EXE `63b4a24a...` 与DLL `7c8ddd80...` hash见H1601 evidence | **PASS_SCOPED** 原TLS、Rust/OS、真业务、Stop，不是GUI手工点击证明 |
| 同账号Windows+Linux不同安装、各自自动地址 | `8a31375e` Win Alice 与 Linux Bob 同用户名，Linux ID独立0600持久安装路径，Bob 真OS `10.66.0.130/32`，互不冲突；Carol/Dave/Erin各独立/32 三AEAD | **PASS_SCOPED 真身份/租约隔离**；无需第二Windows Wintun；跨OS不证明同Windows宿主两个全隧道路由 |
| 五客户端真实150s混合小中UDP/TCP | 一次五端双向 UDP 首次唯一交付 `636494`，发送与接收逐客户端计数匹配；真TCP client双向有效帧 `1458`、invalid0，最大活跃无交付`63ms`；测试专用业务倍率`0.7`，Linux模式Normal/Auto/Game2/Game4/Fixed受本场实际选择约束 | **PASS_SCOPED 150s**，只含256/1120B UDP及小TCP帧；**近MTU、30%高损真实五端、单向稀疏/p99/queue age仍NOT_RUN** |
| Windows单端退出，其余仍业务、最终共享server退出 | 真实 Alice owned WAL/Rust Stop 后，Bob继续4内核UDP，四Linux client+共享server TUN Stop、reader_joined1、queue/drop/backpressure 0，netem/WSL/Npcap清理 | **PASS_SCOPED** 一个Windows Wintun与Linux TUN共享服务端；用户明确不跑同宿主多Wintun，H1587原route/WAL FAIL保留，标未支持/未验 |
| CPU/容量与长期 | `8a31375e` outer kernel上下行**合计**稳态20–121s中位108.834Mbps、Win VM 4vCPU、CPU忙碌峰52.7%、内存可用最少10.762GiB；老`8c0421c3`倍率1.0外层~152Mbps/CPU峰92.6% | 两次不同runner不是CPU A/B；更高同VM压力不能以PASS_150当完成容量或L3；ARM64老源两次1800s另见H1501独立证据 |

本源真实所有客户端与服务端二进制哈希见H1601字段，Go/Rust原产品后端有真实TLS/Rust M4/内核实际输出。不把原失败`43024873684` 0.6发生器参数错误、`43027647645`工作流YAML错误归产品，也不抹掉Action FAIL；仍不能据此宣布028全覆盖。用户已明确多Wintun场景不跑，**其历史FAIL不等于新平台已通过**。


## H1602 当前SOURCE真实内层MTU短场（Action在途、不能提前判PASS）

只补 H1601 150秒业务中缺失的近inner MTU包型：**一台Windows signed Wintun＋四Linux真实TUN**，loss0/单程200ms、已认证真实IP/OS MTU readback，五客户端各`min(client,shared server)inner OS MTU-1`、`MTU`的真实IPv4/UDP总长两次（20次原字节回声）；DF1`MTU+1`仅观察OS errno/发送，不能虚称业务首次到达。仍需Windows先owned Stop、Bob仍能真实内核UDP、全六owner Stop、WAL/netem/WSL恢复。源标记`[plan028-h1602-near-mtu-five-native]`，本源 Action 与原始artifact未收前 **NOT_RUN**。不重跑同账号150s/30%冷场，不测多Wintun，原H1587历史FAIL限制仍保留。

## H1604 当前同源真实轮换与Game兄弟持续（原Action复用）

H1600 Action`43027983611` SOURCE`8a31375e36bb6a93860c5579e64b4a39d0b6e346` 原生日志比原150s Strict报告多给出真实 A→A+B→B 与单lane证据：Bob Normal Auto B gen2先authenticated Health/route promote，A grace17.773s后exact Stop；Carol Game2新两lane都原TLS/Rust M4到位后overlap commit，旧组14.5s后Stop；Dave Game4仅换lane1，server `sibling_lane_restarts=0` 与其它三lane保持，Erin outer1280 Normal新B ready后老A 10.109s后Stop。各事件的原始日志SHA256/实际触发时钟见 [H1604证据](../evidence/M0/PLAN028-H1604-SOURCE8A313-REAL-A-B-GAME-LANE-ROTATION-20261111.json)。全程五客户端真UDP/TCP持续收件/0 invalid/最大活跃UDP间隔63ms，最终六owner Stop；**一场已成功的原网络材料离线重算，未新增Action**。Windows默认轮换0没有被本场开启，不拿Linux轮换代替Windows轮换；候选B失败保A本源未触发，老ARM64 hetero 1800s source`1211fd51`部分按未改组件复用，不移植产品二进制hash或结论。

## H1605 近MTU历史失败与一场新测试

H1602三条原生Actions `43034982111/43035399302/43035735021`均在Ubuntu安装NASM时遇到外部包仓库DNS故障，**真网络NOT_RUN**。此后只按已核实SOURCE`8a31375e36bb6a93860c5579e64b4a39d0b6e346`成功Action`43027983611`原Windows与Linux正式原生ISA-L构件复用，前置校验完整Action/SOURCE/两SOURCE产品零diff、五实际binary SHA。下一Action的新Harness源码与旧Binary SOURCE分别留痕，原默认outer1460/内层OS预算不变；它是20次短真UDP near MTU+Stop，不是150/600s新负载，更不运行多Wintun。具体原因/H1605新凭据见 [devlog](../devlog/M0/20261111-PLAN028-H1605-RECOVER-CI-AND-REUSE-VERIFIED-BINARIES.md)。

## H1606 WSL主源DNS短路后的同SHA镜像回退

H1605 Action`43040746444`原Linux和Windows正式构件/ISA-L SHA复用PASS、Npcap安装及退出清理PASS，但Windows hosted runner下载`releases.ubuntu.com` Ubuntu24.04.5 WSL镜像时报告`No such host is known`，真业务/OS MTU场 **NOT_RUN**。新SOURCE仅对H1602一个测试加官方Ubuntu镜像备选，继续使用原24.04.5签名分发文件的精确 SHA256 `bb415d8248...64ac6039e`，下载失败不得跳过校验或造假。镜像是否可下载须以新Action实测结果判断，不扩展为Windows与Linux客户端功能结论。H1596/H1601已通过原真实150s仍可复用，用户排除双Wintun不变。

## H1607 最新近MTU真实结果：原生环境阻断，不是产品PASS/FAIL

SOURCE `c3a4690782a84df167fc496d61f2fe02979b2d7e` H1606 Action [43042125895](https://github.com/lly8666/wbd-next/actions/runs/43042125895) 整体 **FAIL**；同源治理和治理维护 `43042125801`/`43042125943`均SUCCESS。原始官方镜像备用成功并经SHA校验，WSL2真实guest探针PASS；但下一步Linux underlay RST配置调用`wsl.exe`挂起120s、原native job`130598171269`失败。**真实TLS/Rust、签名Wintun OS、近derived MTU 20次真UDP、六owner Stop全部未开始/NOT_RUN**。已核实本次 Windows/Linux 原生ISA-L产物与旧SOURCE8a对应、Go/Rust正式源码无差异，Npcap安装与最终cleanup通过；它们仅是构建/环境preflight，不是近MTU业务通过。原始ZIP `13866116591` 和 `13866761087` 单文件hash、第一失败、环境收敛及停止重复派发决策见 [H1607 evidence](../evidence/M0/PLAN028-H1607-SOURCEC3A-WIN-WSL-RST-CONTROL-TIMEOUT-NOTRUN-20261111.json)。同一宿主重试已超性价比，**停止同族反复派发**；原 H1601 150s、H1604源锁轮换和旧ARM64两场1800s正向不作新源码无据晋级。Windows L3需独立控制器/DUT、GUI人机与部分路径恢复及nearMTU仍限制。PLAN028 **IN_PROGRESS**。

## H1609: Two real, independent parallel Linux native path-change Actions from identical prebuilt Go/Rust

User skips H1602 near-inner-MTU true datagram scene. Near-MTU remains NOT_RUN/environment blocked; it is not a product pass. H1608 ran two separate Ubuntu x86_64 Actions with the same genuine source8a313 prebuilt Go TLS/Rust ISA-L client/server/so, no Go/Cargo compilation and a zero source diff on Go/Rust/fixture. Full originals and SHA in [H1609 evidence](../evidence/M0/PLAN028-H1609-SOURCE196D-PARALLEL-PREBUILT-NORMAL-GAME4-PATH-20261111.json).

| Real native scene | Action, original artifact | First-pass evidence and true scoped verdict |
|---|---|---|
| Normal / FEC Off / Auto IP, real source4 and MTU migration | `43046531699` SUCCESS; ZIP artifact `13866924204`, SHA256 `2899cdea221be37b2669cf3cb03869ee0554575b810cf4c3d4b6ec1c38e8615f` | `.2→.3`, physical MTU1280, derived TUN OS MTU1209; authenticated Auto OS lease `10.66.0.153`, TLS/Rust new B before A exact Stop; 5 original + 5 post-switch kernel UDP and shared Rust one-reader `10/0/0/join1`: **PASS_SCOPED Linux x86_64** |
| Game4 / explicitly fixed6 / Auto IP, real source4 and MTU migration | `43046531950` SUCCESS; ZIP artifact `13866424747`, SHA256 `c14ba91a95d1d6bba3ece7725230452ce409b0a4f597d2e3003fc5e24679229e` | `.2→.3`, physical MTU1280, derived TUN OS MTU1178; genuine 8 standard TLS ClientHello (two generations ×4), B remote Rust M4 authenticated before old A exact Stop, parity both generations, single reader and 5+5 kernel UDP: **PASS_SCOPED Linux x86_64** |

Game4 fixed6 was test-only explicit; product FEC default is Off. These are not Windows Wintun, new inner-MTU-boundary actual datagrams, independent Windows L3 or 30%/250ms pressure. Retain earlier failures and exact SOURCE. PLAN028 remains IN_PROGRESS.

## H1613 复用正式Go/Rust产物的两条原生生命周期场景（不同Action）

H1611/12 Linux x86_64、正式二进制SOURCE`8a31375e36bb6a93860c5579e64b4a39d0b6e346`、原Go TLS＋Rust ISA-L三个实际文件hash均核，未重新编译。原始 [H1613 Evidence](../evidence/M0/PLAN028-H1613-IDLE100-DEAD106-PREBUILT-X86-NATIVE-SCOPED-20261111.json) 及 [devlog](../devlog/M0/20261111-PLAN028-H1613-COLLECT-IDLE100-DEAD106-REAL-ORIGINAL-LIFECYCLE.md)。

| 功能/入口/默认 | SOURCE / 独立Action / 原始artifact | 真实读回/结果/限制 |
|---|---|---|
| Normal FEC Auto**显式**、100s零业务再唤醒（默认FEC Off） | 测试`c066edd4`，`43050188977` **SUCCESS**，ZIP`13869171897` SHA`e3a61b7382fcdfc16b28ce640d1e00e0eb8a6579882f270fedd187b2b0b57e0b` | 真原TLS/Rust、64首交付、两端Auto applied profile5，100秒无业务后1真UDP回声＋双端owned Stop。**PASS_SCOPED Linux x86**；不是Windows idle。 |
| Normal FEC Auto显式，双边100%真实丢包106s、Health90终止后原业务重认证 | 初始`c066edd4` `43050188879` **FAIL**（过时测试字符串，原ZIP保留）；修正临时fixture测试`44593a822f29d2d87b896349b0b9a41159de1a18` `43053067266` **SUCCESS**，ZIP`13870247251` SHA`b44657c62ff05f27a7f06a52d031048b87b1e7c74fa5271a0ea26cb33c89ffe2` | 两端native `authenticated_dead_or_peer_retired`、旧owner先Stop、新真TUN流触发第二Go TLS/Rust M4 `NATIVE_READY`、恢复1真UDP回声、双端最终Stop。双边qdisc实际drop正数由原夹具assert、绝对值未导出。**PASS_SCOPED Linux x86**，没有新Windows/L3资格。 |

H1602近MTU用户要求跳过，保留原NOT_RUN；双Wintun不跑；Linux本轮两场成功不代表028全收口。

## H1614 高效并行真实Native验收入口（本段不是测试PASS）

**仅两个独立场景**，均复用已签SOURCE`8a31375e`正式Linux x86原Go client/server＋Rust ISA-L三件、每文件SHA及当前产品/原OS夹具零源码差校验，绝不再次Go/Rust编译。新增独立push Action：`m0-plan028-h1614-normal-failed-b-keep-a.yml`（Normal Off Auto IP；只阻断B的新物理源`.3` TCP443/要求内核drop计数、B确实失败且A发一个新的真UDP回声，放开后新B3 TLS/Rust M4、A精确Stop，5次切后UDP及OS TUN MTU）、`m0-plan028-h1614-game2-off-native-path.yml`（Game2 Off Auto，真物理源/MTU变化，标准4条两代TLS ClientHello、2lane A+B→B/真UDP/Stop）。两Action分别一场、不同Runner并行；其他Normal/Game4成功场不重跑；当前源码、测试产物SOURCE分别留痕。**实际Action/原始报告未结束前NOT_RUN**。详见[H1614 devlog](../devlog/M0/20261112-PLAN028-H1614-REUSE-PARALLEL-NORMAL-FAILED-B-AND-GAME2-PATH.md)。用户跳过nearMTU及多Wintun，Windows独立DUT L3仍未验，默认outer1460/FEC Off不变。

## H1615 两场 H1614 原FAIL精确分账及不同条件复验

当前测试源码`9a5d4531904c9d124da77037bce969b8cc70c6be` 两独立原生Action均整体**FAIL**：`43060138936` Normal 同时切物理源`.2→.3`、B2新源真实内核TCP阻断1 packet/原Go候选失败old_untouched，旧A PID存活但新增内核UDP超时，故**A业务不通过**且未解禁/未Stop，不能当“候选失败留A”PASS（物理首选出口改变使旧A并非已证健康）；原ZIP`13873157272` SHA`7775560eb4212f5ee4ebbdb7a812213b18e6fce6280897a4fa10b0efcbe223d1`。`43060138947` Game2 Off真实两代2×2 Go TLS/Rust、新B ready与旧A精确Stop部分通过，却因旧原夹具Game4 `remaining_flows=4` 错套Game2真`2`，后续新真实UDP与最终Stop **NOT_RUN**，原ZIP`13872947708` SHA`660665987ee6dbc4fb4e51ec329a5cee74c990941aacc6bc98e61acc6dcf3d8c`。原失败均保留。

H1615目标是**两条独立Action、各一个网络场景、各复用完全相同H1600 source8a三件 Go/Rust ISA-L 已校验二进制且产品零diff无重编译**：Normal仅**相同原物理路径**下显式5s冷轮换，定向拒绝B2/Bn新TLS端口、原A真实UDP必须在拒绝期收到，之后解禁并二次原TLS/Rust M4、A精确Stop及新业务；Game2只在临时脚本精确改3处旧Game4流数断言为2，仍要求真实物理路径迁移/四条标准TLS ClientHello/MTU/前后UDP/所有Stop。新Action结束前两场均**NOT_RUN**。用户跳过nearMTU及双Wintun，默认FEC Off/轮换0/outer1460不变；见[H1615 devlog](../devlog/M0/20261112-PLAN028-H1615-REAL-FAILURE-RETAIN-AND-DIFFERENTIATED-PREBUILT-RETEST.md)。

## H1616 Game2真实原生完整通过；same-path候选失败保留A仍待定向收尾

SOURCE`9148b784254bd7552ea7b60f81578a1f484d4c3d` Action`43061710360` Game2 Off Auto/两lane×两代 **SUCCESS/PASS_SCOPED**：来源S8a原Go/Rust ISA-L正式产物无编译；原artifact`13874290798` ZIP SHA`eca91b8eefa411113522e23e08908bf3da4167f12886723779e12b8c5432aa86`，真实四条标准TLS ClientHello/ServerHello无私有前置、两IP各2、B原Rust M4 authenticated、旧A精确Stop、物理MTU1280→TUN OS1193、前后5+5 UDP及最终所有owner Stop。旧H1614 Game2 `43060138947` 因原夹具误用Game4剩余流数断言FAIL仍保留。Normal候选B同物理`43061710140` **FAIL**：真B2冷TLS内核丢弃、A保持并交付新增UDP、解禁后B3真TLS/Rust Ready/A精确Stop，但测试意外5s又触发B4，最后UDP超时，尚未全通过；原ZIP`13872369891` SHA`6cf1b8d0c2269da00bcf546c3155e138c52fc714b96e2c21a7833a88cb1d6095`。H1616仅把该测试显式轮换interval设30s（原默认仍0）一次，防止B4与10-20s退休期重叠，**新Action未结束前NOT_RUN**。详见[H1616 devlog](../devlog/M0/20261112-PLAN028-H1616-RETAIN-B3-B4-INTERFERENCE-ONE-FINAL-TIMER30-NATIVE.md)。用户跳过近MTU、多Wintun，独立Windows L3仍未验。

## H1617 原生B失败保留A闭环＋Game2 Off物理path两lane（原binary SOURCE`8a31375e36bb6a93860c5579e64b4a39d0b6e346`）

完整[原始artifact SHA、TLS标准握手、原native kernel UDP、Stop和历史FAIL证据](../evidence/M0/PLAN028-H1617-SOURCECF03-PREBUILT-NORMAL-FAILED-B-A-LIVE-GAME2-OFF-20261112.json)。

| 组件/正式入口/默认 | 真实原生资格与精确源码/Action | 限制 |
|---|---|---|
| Normal Off Auto IP，**仅测试显式**30s同物理源Cold轮换（Linux正式interval默认0） | H1616 harness`cf03ab6b59b63c5f7b247a81826bc465fec6947f`，原bin`8a31375e36bb6a93860c5579e64b4a39d0b6e346` Action`43062378203` **SUCCESS**；原ZIP`13874281596` SHA`9043c81357df699d77590e16f30d524b1ae4e1f9ec1421ad452d42d1da734fb2`。源4未改、内核仅B2真实TLS DROP1、Go候选失败old_untouched、A仍真kernel UDP；解禁B3真实TLS/Rust Ready、旧A grace16872ms后精确Stop、B3再5/5真UDP、双方最终Stop。 | **PASS_SCOPED Linux native同物理A可达条件**；未解决原SOURCE9a旧物理改变时A新UDP不达的失败；不是Windows或L3。 |
| Game2 Off Auto IP / 两lane / 原 outer1460 → 物理1280的真实路径预算 | H1615 harness`9148b784`、原bin`8a31375e36bb6a93860c5579e64b4a39d0b6e346` Action`43061710360` **SUCCESS**；artifact`13874290798` ZIP`eca91b8eefa411113522e23e08908bf3da4167f12886723779e12b8c5432aa86`。原TLS443四ClientHello（两代各2、无私有前置）、真实OS TUN1193、B组remote M4后A+B→B、前后5+5真UDP、所有owner Stop。 | **PASS_SCOPED Linux native Game2 Off**，旧H1614 Game4流数断言误判FAIL保留，不是Fixed6模式。 |

七模式：旧SOURCE`0cda9157` Action`41970545107`七场/28次认证轮换总投递`16220`收到`16219`（Game2 Off丢1），**旧SOURCE scoped**；当前产品源`8a31375e`已有Normal Off/Auto、Game2 Off、Game4 Fixed6及Normal Fixed代表正证；**Game2 Fixed6、Game4 Off和本源Normal Fixed6最高强度未以相同新源码全复测**，按既有未改组件证据限定复用，不把缺的模式标PASS。此条不是新七场矩阵任务，不扩展029/030。用户跳过近innerMTU、多Wintun，Windows idle/物理path和独立DUT L3仍NOT_QUALIFIED。028 IN_PROGRESS。

## H1621 Windows idle105 场景MTU纠错与七模式源锁核对

H1620 Win/WSL2原生Action`43066195581`整体 **FAIL**，原二进制SOURCE8a Windows＋Linux正式Go/Rust/ISA-L SHA、签名Npcap、真实WSL2内核TUN先决条件通过，但原105s场景`tun_mtu=1400`与本次`native_outer_mtu=default1460`冲突，原生MTU契约正确拒绝，原Go TLS/Rust业务**NOT_RUN**。保留原artifact`13876720931` ZIPsha`ba9f0a87b778601de85a5d5da5c68cc2cf1e6ddbf5fa5935eca4027a3f4e47f4`和guest ZIP`13876690824` SHA`90f7d7ab18fd190e93bc97c110e6d4d0ca1f8fdcd35cc4b49653267f265659f5`。H1621新测试场景只改`scenario_id`和`tun_mtu 1400→1460`，原旧测试场景与正式产品源保持不变。包装校验完整逐字段来源锁克隆，原MTU契约default1460/1460 PASS、default1460/1400必须FAIL；独立单场Windows signed Wintun+WSL2 native仍复用H1600预构件、无需重编译，正式业务/Stop待原始目标Action而不能因包装成功记PASS。

[H1621七模式/默认值SOURCE审计](../evidence/M0/PLAN028-H1621-SEVENMODE-DEFAULTS-SOURCE-AUDIT-20261112.json)为**静态源代码覆盖**而非新原生网络测试：Linux默认外层IPv4 MTU1460、Normal和Game FEC Off、rotation0、Game4默认copy stagger0/4/50/140ms；Windows的七项normal/fixed/auto/game2/game4/game2-fec/game4-fec对应Linux五种基本mode和Game固定6开关。旧`0cda`七模式28次交接/16220投递16219回声仅旧SOURCE PASS_SCOPED；当前产品SOURCE8a并无每项独立七模全新组合资格，严格保留不足，028 IN_PROGRESS。

## H1623 当前正式SOURCE8a Windows signed Wintun＋Linux WSL2 真实105s休眠唤醒（已完整验收）

源锁Harness `0577bb29`，原正式产品二进制SOURCE `8a31375e`、成功build Action `43027983611` 原Windows EXE/DLL与Linux原Go/Rust ISA-L三件均只复用重验SHA，无重编译。独立目标 [Action43110135433](https://github.com/lly8666/wbd-next/actions/runs/43110135433) overall SUCCESS，原ZIP artifact `13895333759` SHA256 `49d03fc3a5020af8484ca1b41dd8452f74fb5906bcf74cce0c8aa6a838286e13`，37文件CRC及原report SHA `0a6b9d0cb1d5dde9a52871690dd7f099f7eb8a9eb1cb82dd80d5050bbb6d0c55` 核实；真实Ubuntu WSL2 guest kernel boot artifact `13896036874`。原Go TLS443／Rust M4、官方签名Npcap 1.88＋一台Wintun、Windows Wintun OS MTU **1389**／Linux实际TUN OS MTU **1389**，原外层完整IPv4 MTU配置 **1460**，原FEC **Off**、原Windows `auto_lease=false` 手动/32，非Windows Auto-IP。

**真实105s无业务** → 实测 **108.48s** 两端原生owners仍活 → Linux和Windows双向真实UDP唤醒PASS；后续独立60s、双向各10Mbps、25ms、0%请求loss，Windows发 **99,497** /Linux首次收到 **99,497**，Linux发 **99,551** /Windows首次收到 **99,551**，重复0、无效0，实际本源UDP first-delivery两方向100%；原生TCP双向及双方全部**owned Stop**、Windows WAL原样恢复和Npcap清理PASS。真实原始源记录完整[H1623证据](../evidence/M0/PLAN028-H1623-SOURCE0577-WINDOWS-SIGNED-IDLE105-PREBUILT-TWO-OS-NATIVE-20261112.json)。

限定 **PASS_SCOPED**：此场没有单独量化Health 15/90 heartbeat次数，只证明owner存活及真实UDP wake；没有Windows Auto-IP、物理切网、新B失败、独立Windows物理DUT、单向p99/满压或600/1800s L3。旧H1618/H1619/H1620/H1621 pre-business FAIL Action保留；不会因现在PASS覆盖这些历史错误的原Action结论。七模式完全新SOURCE矩阵仍缺代表。用户跳过近innerMTU和同宿主多Wintun。PLAN028仍`IN_PROGRESS`。
