# 10 生命周期、自动档、配置与观测接入

## 原功能复用的精确边界

Go继续决定认证/地址租约、lane建立/rotation/idle、auto FEC升降、server policy、DNS与分流、GUI状态；Rust只执行逐包行为和提供客观事件。不得在Rust另写一套auto controller与Go同时改档。2026-10-18新工作包的档位、初始化/升降/有效样本规则以[FEC v2第7节](../FEC_V2_BALANCED.md)为准，覆盖下文“旧判断/滞回/配置定义照搬”，保留唯一控制点和本页生命周期要求。旧N2效率/GE尾延迟OPEN保持，旧N4/GUI/打包收尾从精确SHA导入。

复用原 `docs/PARAMETERS.json` 为唯一配置语义来源，R0形成迁移列：旧key/default、解析位置、新effective位置、CLI/GUI/help、适用模式、测试ID。不另造第二本手写参数目录；尚未移入的项列DEFERRED及原因。外层加密、FEC mode、自动普通/激进、上下行独立、服务器每client策略不得被统一成进程全局值。

## 真实业务活动与idle

TX在合法真实payload被接受进入tunnel时刷新payload_activity；RX在真实业务首次交付时刷新RX业务活动。health、receipt、keepalive、parity、重复包、repair均不刷新这两个值。keepalive丢失不会改变“最近确有业务”的事实，不能以没收到keepalive判无业务关闭。

Rust计数器记u64单调timestamp，Go读取后按原双向idle策略决定宽松关闭；不是等2s统计刷新才接受业务。Go决定休眠发Suspend(epoch)，Rust先停止新lane工作/有界处理已接受队列，再quiesce旧lane；已排入的业务及期间新包必须导致取消本次suspend或请求Resume，不能黑洞。

休眠保留业务入口监听，Rust遇第一真实payload立即发WakeDemand并保存有界首包队列；同一休眠epoch只发一个未完成WakeDemand，不每包建连接。Go建lane成功后排队包仍在有效期限才交付；失败/队列满/过期有原因计数。idle关闭不必卡在毫秒精度，首包触发重建不得等待下一2s GUI刷新。

“一个未完成”是合并并发请求，不是整次休眠只许尝试一次：建连失败/取消/超时须完成或清除对应in-flight标记，并按原有界退避允许后续真实业务重试；旧epoch的完成事件不能清除新请求。持续发送但对端不响应属于liveness/黑洞恢复，不是payload idle；不能用同一个时间戳混判，也不能让control流量把休眠永久续住。

## Auto FEC接口

Rust每方向提供实际source/parity/repair/received/recovered/late/host_drop/partial(k,r)/first_delivery样本和quality freshness；Go沿用旧成熟判断/滞回，发`SetTxFec(profile,decision_revision)`。TX仅在新block生效，旧block按旧r关闭/有界drain。fixed/off不构造auto控制器；Game不自动调档；Normal aggressive规则沿用旧配置定义。

receipts说明外层record是否到达，不等于线路原始loss（重传会掩盖损失），FEC恢复率也不等于原始loss。保留发送attempt/首次/repair分类，GUI显示估计口径/数据年龄；无样本显示未知，不显示0%。质量报告沿用已有抑制/合并逻辑，可与08 receipt共用control bundle和一次唤醒，但二者判断数据不同，不强迫每2s发固定包。

## 配置安装

Windows冷层运行时去PowerShell的新增授权见[PLAN-010](../../decisions/M0-windows-native-migration-2026-10-19.md)：沿用Go原生API/owned WAL，M4接CLI/GUI，M0接Stop完成边界；不改Rust热路径或另造网络管理服务。Apply/Cleanup/Recover不调用shell，构建/Actions脚本不在清除范围；完整网络及WFP未验门仍保留。下文“不授权重写原OS网络管理”不阻止这项已明确授权的定向移植。

每个命令带revision，返回accepted/applied/rejected及effective值。可在block边界生效的项明确报告pending until block；cipher/认证/网站/地址等需新lane的项通过旧rotation/重连机制，不原地修改密钥。UI必须显示连接状态与清理未完成原因，不把busy吞掉留下永远转圈。

迟到旧revision的applied回执只作历史事实，不能覆盖UI当前选择或把另一client/方向的配置标为生效。Go程序与Rust库按兼容ABI/能力和配套manifest一起打包；不能用“各自都编译成功”替代实际加载/生效。DNS、借站/服务器地址及direct出口沿原旁路与资源归属规则，防止控制连接再次被TUN接管形成循环；这不授权重写原OS网络管理。

`--tls-startup-padding`仍有限、仅原触发条件，off/固定/自动都按旧配置决定，不因Rust record重写漏掉。DNS主备、LAN/中国IP规则、默认IPv6空路由及原安装策略留Go；新引擎分类用已发布不可变路由快照，不每包问GUI/查系统注册表。

direct-TCP/gVisor保留热路径例外：从Rust移交时批量至多32包、总等待上限仅已有ready（不攒包），明确owned buffers；该流由Go子路径负责，不在两端同时收发。回传队列有界，单direct流拥塞不能堵全部tunnel。CPU在Go与Rust之间按进程/线程分账。

## 低成本观测

每owner普通u64计数，snapshot每2s或显式请求合并；逐包不做JSON、字符串格式化/日志mutex/全局atomic直方图。常态保留sum/count/max与少量对数桶；诊断更细时间戳/10ms首到桶按显式开关使用预分配buffer，普通默认off另跑性能。

必须持续有：offered/accepted/first_delivered/duplicate/late、fresh/FEC/replica/repair/control字节、每层drop、effective MTU/cipher/FEC、timer lag、queue oldest age、shadow命中/expiry/pressure、socket实际buffer。unknown不写0，diagnostic开销单列。任何metrics读取不等待数据面全局停止。

## 测试

连续真实业务但keepalive全丢；只有keepalive应能idle；Suspend与新包同轮、首包重建失败/超限；fixed/off不误auto；两client不同cipher/FEC；上下行不同档；GUI已保存但被拒绝要显示；default与CLI/config覆盖顺序；最后quiesced后设备清理。适用的旧功能逐项有生效证据，不只检查字段出现在配置文件中。
