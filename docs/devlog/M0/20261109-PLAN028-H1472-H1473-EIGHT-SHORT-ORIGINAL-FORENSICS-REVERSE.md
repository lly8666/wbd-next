# PLAN028 H1472/H1473｜八场已做真实五客户端180s短测：无条件排队失败、换代对照与AB/BA旧源复判

**出发点（客观是否可达）**：已有H1360旧6c5零损75Mbps/五用户原生180s确实范围通过、source66fb新H1461完整600s 75Mbps却真实Alice下行缺32/服务端待发队列丢45，长1800s真实五客户端所有M4轮换和六Stop且服务器队列0，但0%配置丢包Alice下行缺351。属于**不可放过的严格零损可靠性问题**，不是吞吐/认证/Stop架构根本不可用；“0% tc注入丢包”不保证raw socket、虚拟核调度、内核队列天然无丢。H1292只处理旧FIFO调度机会，H1461 near-full batch8改法没有消除75Mbps服务器Full。历史PLAN026 Linux SOCK_RAW接收缓冲增大后100Mbps原始内核drop归0；H1298/H1300说明上层发成功不等于远端raw收成功；H1302 ARM64宿主全核≈99%与本次x86宿主分开。目标75Mbps在某源和宿主下物理可达，但零损SLA仍未达成。

**真正恢复现场**：H1467原生[Action42590018240](https://github.com/lly8666/wbd-next/actions/runs/42590018240)两台独立ubuntu x86，每台连续两场180s Go TLS443/Rust M4 ISA-L、五真实授权账户和六个owned Stop；第一台同一源66fb Alice Normal 75Mbps+4位2Mbps，256/1024混合 vs 1024B全大包，两场每个用户双向 **0个唯一UDP缺包、5租约队列overflow=0**，服务端进程平均单核CPU28.6%→26.0%，这是同VM顺序差分不等于经随机BA验证的优化。第二台相同SOURCE/宿主 Alice12Mbps+4位2Mbps：静态无轮换5人双向0缺包、queue0；真实M4换代 **25个下行唯一UDP缺包**（Alice16，Bob4，Carol4，Erin1，Dave0），原服务端5租约队列仍0，原H1286五人M4换代 `PASS_ALL_FIVE_SCOPED`、零配置告警。Alice缺包阶段[first_wave7,recovery9]对应她gen1→2原切换接近业务+38秒，gen2→3接近业务+138秒；500ms owner stage旁证是阶段级相关，尚非逐个丢包时间戳因果证明。旧H1286刻意不轮换却打印`ROTATION_CONTINUITY_NOT_PROVEN`的5条是**没有请求轮换而旧审计器误判**，不可计作产品换代失败。

**真实SOURCE反序AB/BA**：[Action42590601995](https://github.com/lly8666/wbd-next/actions/runs/42590601995)复用旧source6c5与新source66fb两套各自真实原Go/Rust/ISA-L x86 ELF二进制，三份实际SHA256分源锁；同一VM顺序旧→新两场都零应用缺包/队列overflow0。另一台VM倒序新→旧：新版Alice应用UDP不缺包，但真实server per-lease `pending_overflow=32`、`downstream_full=93`；旧版Alice上行缺16、下行缺57，总73，server queue overflow78、downstream_full130。即使新版应用0缺包也**不能把已触发真实队列溢出的场景判为严格PASS**。原来“旧码一定比新码稳定”、“新批排FIFO已治好满队列”均不成立；现象仍受底层host突发/每核M1消费速率影响，前者尚未被因果分离。

**必须区分双层CI结果**：上述八场真正180秒双向UDP/TCP、服务器M4、六最终Stop均完成，原始4份ZIP IDs **13661277093 / 13660868907 / 13661168078 / 13660943781** 全部CRC_PASS，ZIP SHA256分别`aa25c612…`、`5ccdcc70…`、`1650cc93…`、`44eb133d…`。两个原始Action的jobs依然结论**FAILURE**，是执行后审计工具错误地查找`paired/<case>/fixed-kernel-result/h1250-matrix-plan.json`；真正文件路径是`paired/<case>/h1250-matrix-plan.json`。因此现有原始产品结果既不能被CI红色误判为8次产品全失败，也不能因为原始业务完成就给全部PASS。H1472只提交脚本源锁原四ZIP离线逐用户/方向/阶段重算，严格5项PASS/3项FAIL并保留旧Action FAILURE。不同的原生产SOURCE6c5/66fb与新复判SOURCE分别有明确标注，绝不改原ZIP。

**下一组唯一新原生短对照 H1473**：因为静态→换代只跑过一个顺序，独立x86同宿主在**同一原SOURCE66fb已验SHA二进制**下反过来按`rotating12 → static12`连续两次180s，原Go TLS443五身份、真实换代/六Stop、500ms原始M4+RAW socket及CPU读取全部保留。若倒序仍为只有轮换场缺包，且Stage与M4交接同一窗口，才考虑代际接收/Old-owner Grace/FIFO退出的最小产品变更；若倒序变成第二场缺包则先归宿主时间顺序/软中断噪声，不补包掩盖。该回归只能定向验证 Linux L2，不能替代正式Windows Wintun原1800。H1473新工作流仅一Runner两个原生180s，不重复四个旧场景或长测。

**工程判断**：75Mbps不是架构性不可达；业务丢几十包在数百万包里比例不大，但对严格零损资格是明确FAIL，不能改分母掩盖。真实换代在有原始六Stop/M4接管的情况下仍发生小量低载丢包，重要性高于多加8个缓存槽。下一步分流比较每代的服务端TUN offer→M1队列/RAW TX是否被内核接受→客户端raw/socket进度→M3 TUN→应用唯一UDP，按CLOCK_MONOTONIC同机对齐与真实新旧代端口，仅碰已证有问题的边界。不先动TLS外观、AEAD/PN/FEC、MTU和其他用户。源548既有75Mbps 28丢/5 overflow及SOURCE66fb 600s 32/45, 1800s 351/0等历史 **FAIL_SCOPED** 均保留，ARM64两独立1800 **PASS_SCOPED**、Windows600 **PASS_SCOPED**、Windows原Hosted1800 **NOT_QUALIFIED**、H998旧HOT MTU **FAIL**、Android/物理 **NOT_RUN**。PLAN028 IN_PROGRESS，不开启PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Eight immutable native original x86 five-client source-locked stress offline verification, fix a source-specific offline auditor path only, and one reversed-order same-product short native differential; no product, wire, crypto, MTU or configuration changes."}
```
