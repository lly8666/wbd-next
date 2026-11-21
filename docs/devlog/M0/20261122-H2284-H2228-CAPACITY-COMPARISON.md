# H2284 · 复核旧H2228高速三Runner与当前Windows→ARM双组三机夹具的真实性能差异

## 用户纠正与历史证据
用户指出原项目H2228三Runner数据通路曾远快于新 H2276–H2283，虽启动较慢，要求不要把低速测量夹具问题归到产品、应复用旧夹具经验并尽快优化原WBD。已查当前正式实验分支旧文件：
- `docs/evidence/M0/PLAN029-H2228-THREE-ARM-RELAY-GE200-REAL-TCP-20261120.json` 精确源 `2a2f809592856411daa70b3c043b2f6430774ce8`，[Action44705243325](https://github.com/lly8666/wbd-next/actions/runs/44705243325)，**旧原生Linux x86-client＋ARM kernel L3 relay＋Linux x86-server** 的干净0ms/0%八并行 `iperf3 -t12 -P8 -C bbr` 上848.551、下861.757Mbps；原完整WBD弱网矩阵 FAIL（部分冷启动Ready/业务问题），不能把800+说成原WBD 800Mbps。另一次相同拓扑但Tailnet DERP时，参考只有约19Mbps，证明物理/Tailscale组网可剧烈改变结论。
- 旧组件 `tools/m0_h2228_three_runner_relay.py`、`tools/m0_h2228_three_runner_case.sh` 用客户端、服务端各自独立VNI2281/2282 VXLAN到 ARM 路由器，两段独立L2、L3 kernel route、无 NAT，真实中继TTL减一，双方netem各只作用一次，`tailscale0` 的OIDC/控制不被tc阻塞。旧 netns强制 BBR、`tcp_rmem/tcp_wmem`上限64MiB并readback，跑八流而不是四流、tcp-ipfer3底层真实已收bit/s。这些是旧高速**可能的实质优势**，也可能因不同Linux OS、TCP拥塞控制、8流与Windows与ARM不同而无可比性。不可仅凭旧数断言VXLAN优于NAT/Tailscale。
- 旧启动慢原因在workflow明确可见：每个端点先 `m0_plan029_linux_dual_native_build.sh` 编译原 GoTLS+Rust ISA-L、安装iperf3/netns/VXLAN/tcpdump、创建Linux隔离网段，然后以每5秒最多多轮`gh run download`同步真实peer/ready。新H2276–H2283跳过产品编译、两组三台用Tailscale OIDC精确peer加纯Linux relay DNAT/SNAT，准备更快，但之前4流/24MiB上限/Windows默认128KiB偏小，不能公平比旧H2228能力。
- H2281四流25s连续真实Windows2025 Winsock→ARM 400ms RTT无损约8.4Mbps；H2282同组A/B8MiB/A′ 8.829/**227.397**/8.909和8.095/**339.676**/8.605Mbps，但P99恶化；H2283 `96a72df9941b543fac8564f9c8f295dd4c09297b` [44930676830](https://github.com/lly8666/wbd-next/actions/runs/44930676830) 双组七job完整SUCCESS，2MiB两端Buffer A/B/A′ A9.824/**145.346**/9.835、B8.806/**138.082**/9.336Mbps，P99 A407/407/407ms、B422/437/422ms；证明低速重要部分是**TCP应用socket大小**，而不是全链CPU爆炸或Rust丢包。

## H2284 双组三runner精确比较，而不是直接混用旧实验数
新 `qa-h2284-old8-flow-capacity.yml` 专门把**旧高速的八并行/大窗口/连续时长容量门**移入现有**真正 Windows2025 client＋独立 ARM64 Linux kernel NAT relay＋独立 ARM64 Linux server** 快速启动架构，两个互不共享的a/b组三台真VM、同SOURCE、同工作量：
1. `clean_direct`：Win2025 Winsock→同组ARM server 的真 Tailnet 原生内核TCP，不经过relay，不加丢包与额外延迟；8 bulk TCP各25s、每流最多512MiB（避免短流提前退出）＋160小TCP同步观察，Win+ARM实际 `SO_SNDBUF/SO_RCVBUF` 请求8MiB、收端readback、CPU和每字节服务端确认。
2. `clean_relay`：同Win/ARM、同原生8流、同真Tailscale client→relay→ARM 两跳**kernel DNAT/SNAT**，双向qdisc0ms/0%实际发包/丢包计数，OS buffers相同，报告Relay/Direct效率，收**ARM relay host allcore+最忙单核、tailscaled proc CPU秒/25s占单核%**，不再仅因Windows/ARM CPU不满就断言relay没饱和。
3. `wan_relay`：完全同原生真TCP、Win/ARM同socket配置、同两跳relay，分别在两方向真实 `tc` 增加200ms、0%损失（RTT约400ms），保留160次回显的P50/P99/迟回、两方向真实发包计数、服务器接收、三机CPU/relay tailscaled计数。
- 原H2228是 **Linux x86↔x86+BBR/64MiB/两VXLAN无NAT/上行下载都测**，H2284是 **Windows Winsock↔ARM+操作系统默认CC/8MiB/两TS跳kernel NAT、仅客户端上行**。本实验不是“旧路线还原”也不对旧800数字做因果结论；其价值是找出当前夹具究竟是TCP供给不足、Windows↔ARM Tailnet 物理容量不足、还是relay双跳CPU/转发瓶颈。若同组真正clean直接高而经relay下降数倍，下一步优先将旧H2228的独立VXLAN无NAT路由迁移到满足Win客户端原生Wintun路径的可验证跨系统拓扑，**不能直接让Windows Winsock绑定Linux WSL2虚拟VXLAN IP假装本机通信**。
- 源脚本新 `CAPACITY_H2284` opt-in，仅这个workflow扩为8条真实TCP、Win及ARM原生测试应用请求8MiB buffer；旧H2271/Wintun/NPF未更改。中继资源快照按同一阶段开始/结束从`/proc/stat` CPU allcore/per-core、实际 `/proc/<tailscaled PID>/stat` utime/stime 计算，不以进程生命周期平均top的%冒充阶段CPU，不接触生产。要求两组relay `tailscaled_pid_count_common>0`、两个方向netem实际pkts>0，否则不计资格。200ms阶段P50 RTT >=350ms，否则fail closed。由同一8流实接收完成计算goodput，任何不合格网络保留无资格而不冒充产品失败。
- 对旧H2228的高容量门 `800Mbps` 仅在双方“干净direct和clean relay都>800”时记`QUALIFIED`，未达记录网络/OS容量待定。默认只运行轻量静态，带 `[m0-029-h2284-eightflow-capacity]` 标记才运行两组6 VM。复用原三个角色现有源锁run/组认证，不回写历史Action；所有旧测试场景新cap模式的环境隔离单测必须绿灯。
- **当前未跑的仍OPEN：** Windows原Wintun/Npcap＋Go TLS＋Rust→ARM原Rust TUN、FEC2弱网1%/5%、内层M1/M4丢包和两个端点真CPU/P99+original owned Stop。下一步在H2284容量/relay结果可信后优先把原产品业务装到这两组原生机器，以可归因小范围buffer/BBR/FEC2窗口优化，而不是无限增大本地队列让P99恶化。PR#68保持Draft。

```feature-impact
{"kind":"none","reason":"H2284 adds only source-locked two independent native Win2025 ARM relay ARM TCP preflight with 8 real 25s streams and test-only buffers, precise relay CPU; old H2228 product/native results unchanged. WBD Go TLS/Rust/drivers/defaults/Stop unaffected."}
```

## H2284 首轮静态真实性门：未浪费六机的测试隔离失败
- 源 `4c918b6d0a7488b776acf80e80da95889aabe501` [Action44932299370](https://github.com/lly8666/wbd-next/actions/runs/44932299370) static失败（29项其他单测通过），六个真实Windows/ARM角色都按`needs:static` **SKIPPED**；所以该run**没有任何八流容量数据**。具体四个旧夹具单测不兼容显式新 H2284 模式：H2280曾假定始终4流、H2282/H2283原值准备判断没有隔离CAPACITY_H2284开关、H2276 tc qdisc mock未mock新relay_resource_sample而去真正读子进程ps。全部属于测试模式隔离，不是产品或真实网络吞吐失败。
- 修复保持旧单测明确在旧H2280场景要求4流，在新H2284明确开关时接受8流；H2282/H2283原A/B′窗口单测各局部禁用八流profile，H2276 qdisc单测隔离真实 relay CPU sample（真实H2284必须校验procstat和tailscaled PID/CPU，未删任何性能断言）。新真实六机只由明确标记启动，不为静态FAIL声称业务PASS。
