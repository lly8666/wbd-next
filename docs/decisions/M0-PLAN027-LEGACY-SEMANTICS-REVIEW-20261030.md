# PLAN027｜老版语义放宽与源码审查

审查产品SOURCE `08ebf0e2e0e27f055a19e658f05808f691d08fce`；复核至main `1b669b31`，后续是测试/证据更新，下面相关生产逻辑未改。本轮只读代码，没有运行专项产品测试，以下是静态调用链发现，不是实测CPU结论。旧oracle实际读取wobuzhidao@a7a82db3的quality.go/control_policy.go/quality_window.go：Auto才持续统计、1.5–2s随机间隔、有变化才发、缺证据保留未知。

后续接手先对照最新SOURCE：已修复且有证据的项更新状态即可，不重复开发；本审查不覆盖或撤销并行期间的新修复。

## 需要M0修的断点

| 优先 | 现有代码与影响 | 最小修正方向 |
|---|---|---|
| P1 | `wbd-recovery/src/outer_ack.rs` on_feedback只有later SACK产生gap候选；Windows native RX 756/779及Linux embedded 4081传空SACK，Windows还parse_ack_packet(...,false)。去掉Receipt后这条实际路径只能退缓存，不能触发机会重传。 | 贯通老版真实ACK缺口/SACK信息，验证生产候选→quota→原密文发送；不能只给纯函数手工SACK就判产品通过。 |
| P1 | Windows `v4_windows_fec2_owner.rs:675–688`及Linux `v4_embedded_go.rs:6536–6562`提供全量实际k直方图，first_sent已是间隔抽样。Windows `v4_windows_rust_auto.rs:145–146`与Go `fec_v2_policy.go:308–315`仍要求全量k源数/抽样源数≈1；持续较大流量可一直UNKNOWN。最高档1024-PN窗口又包含parity，源样本可能不足每2s512门。 | 区分“采样损伤率”和“实际k概率分布”；同样本数量才能守恒，否则归一化分布而非除以抽样数。按实际有效样本累计，不用旧每tick512门卡住控制器。 |
| P1 | Linux `LinuxQualityTx::next_signal`在bootstrap_only两窗后返回None，但due() 584–590和worker 5957–5965仍把已过next_open当到期；wait函数5318–5322返回0，反馈空转而非睡眠。 | 优先去掉不必要Fixed bootstrap；保留的状态须有完成态，due/next_deadline/producer一致，结束后无到期任务。短业务后闲置看线程CPU，不能甩锅runner。 |
| P1 | 新Fixed START/CLOSE加入了质量统计，但Windows真实Fixed `open_symbol_entry` 171仍仅Auto喂样本，修改放在普通v5路径1592；Fixed readback 761–763与Auto state 204–208还等永不再增长的旧fec_reverse_reports等。纯测试直接喂m.quality_receive绕过了真入口，不能证明已接通。 | 按用户新授权解除Fixed生效对成熟质量的依赖；更新实际调用和读回语义，保留本地配置/真实IO/对端资格的区别，删旧receipt门，不造计数。Auto如需质量也只读新来源。 |
| P2 | Windows `v4_windows_owner.rs:648–660`仍逐包喂旧MatureFirstSend；Fixed `v4_windows_fec2_owner.rs:164–165`仍记旧RxFeedback位图，线上已经不发旧Receipt。 | 清理没有消费者的热状态，保留低频质量和必要修复缓存。只是线上包消失不等于CPU路径已精简；不因模块名M2就全删。 |
| P2 | `budget.rs:247–255`把stage0绕过token不足判断，而receipt.rs:642–645当前唯一一次修复全是stage0。1秒额度仍在，但“8MTU平滑突发界”不成立。 | 修复只为外观，取消首次恢复优先的免平滑语义；复用现有桶，无需另造scheduler。看R/F和短窗突发，别把平均占比当平滑。 |

## 已看到符合目标的内容
HealthClock分开认证活动与真实业务idle，默认15s带抖动、90s失联；质量可合并保活，裸ACK不刷新认证存活。原密文/PN和数据首到路径未因低频反馈改成等待全部旧洞。方向正确，但上表接线/计量问题尚不能用短业务PASS覆盖。

最新H449记录Linux64 UDP短样本Fixed/Auto首发和读回通过，明确不证Auto升降/120s或Windows/C性能；保留其原证据，不宣布该短测试失败，也不能据此关闭上表的持续流量问题。允许按PLAN027§0.1放宽额外证明门，不能通过放宽掩盖空转、静默重传失效或永远不切档。

最小回归纳入原A：已有core反例加实际调用；Fixed短流量后空闲无忙转；持续Auto跨两个档位看真实采样/actual-k/unknown原因及120s缓降；原off 0%/30%两条看真实缺口、发送、R/F与总量份额。相同SOURCE产物复用，一Action一场景，之后继续B/C/必要修复和整体交付，不重跑全历史或另做架构比赛。
