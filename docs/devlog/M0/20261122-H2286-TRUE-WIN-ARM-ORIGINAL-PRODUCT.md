# H2286 · 两套原版完整Windows客户端→独立ARM原GoTLS/Rust服务端性能首测

2026-11-22 / M0 PLAN029 / 实验分支 experiment/m0-029-throughput-arm-fair / PR#68 Draft

## 决策
用户明确要求“win端要完整客户端才能最后测明白性能堵点在哪儿”，不再继续微调空载或裸 Winsock 夹具。H2228旧三Runner Linux x86/ARM64/x86双VXLAN零损8流上行848.551下行861.757Mbps；H2284把8流/大Socket移到Win2025→ARM→ARM两组，真底层直连达到1286/1068Mbps、中继680/995Mbps，A组800门不合格、B组合格；H2285在**真正 Windows 2025→本机 Linux WSL2 kernel DNAT→独立ARM Linux relay→另一ARM Linux server** 成功A468.211/B496.194Mbps，所有双向内核转发/ARM应用实际收包均已读回。这些只证明测试网络，**不是原WBD产品**。

## 新H2286实际整链，而非TCP模拟
引入专用 \`qa-h2286-dual-original-windows-arm.yml\`，唯一显式commit标签 \`[m0-029-h2286-real-windows-arm-product]\`，两套互不共享的(a,b)三台真Runner：
- 一次额外ARM64原生产构件build job，复用 \`tools/m0_plan029_linux_dual_native_build.sh\` 真 GoTLS＋Rust native ISA-L。每组ARM server复用同一SOURCE和SHA256验证的这组 ARM 构件、各在独立 VM 跑。比H2228两端重复编译省准备时间。
- 每台Windows从既有可信的Action44923149093重用**实际原签名Go客户端 wbd-client-embedded.exe＋wbd_engine.dll**，原SOURCE \`c5066db61fc51bafd7c2ad2def3029e615efa777\`；CI先 \`git diff c5066..HEAD -- crates r0/go_overlay Cargo.lock Cargo.toml tools/prepare_windows_wiring.py\` 实际为完全0才允许复用，并逐字节核旧归档manifest哈希。任何产品源改变，**fail-closed要求重编**，不假装旧产品源。Windows每组都安装/校验原签名Npcap1.88核驱动＋官方Wintun0.14.1，从未绕过真实原 Wintun/NPF 数据面。继承 \`WBD_PLAN024_NATIVE_VERIFIED_*\` 真WSL2 vEthernet neighbor/MAC/HyperV仅端口443和源41031的exact allow，Stop后恢复原Windows驱动和仅本Runner的neighbor/HyperV条目。
- 原 Windows Go客户端以 \`--native-v4-product --control-stdin --server-ip <本机真实WSL2 eth0>\` 启动：没有Python/OS Winsock伪装外层TCP，Npcap发来的**真实二层TCP443 FakeTCP外层包**先进 WSL2 eth0，只有 WSL2的4条有界内核iptables对精确来源/目的及443→relay18727做 DNAT/SNAT/FORWARD，Host原Win内核不代理业务、不虚构ACK，恢复原 \`ip_forward\`。ARM relay复用已验证两路真正\`tc\`的kernel DNAT/SNAT，源锁三个身份认证。远ARM server新增 **真实h2286sv netns、veth wan0 10.248.82.2/24、宿主hostveth 10.248.82.1、Linux AF_PACKET raw original GoTLS/Rust、实际Rust TUN wbds0 10.66.0.1/24**；宿主的精准port18727→wan0:443 DNAT、反向conntrack和精准FORWARD/SNAT。wan0只在netns内真实L2链路，没有把tailscale0 L3当Ethernet。仅该netns拒绝Linux OS TCP443 RST，原Go/Rust SYN/TLS/业务自己处理；所有相关内核iptablessysctl仅临时应用、Stop按逆序恢复。若原Go raw TCP无法穿多个conntrack，保留第一层真实坏包/反向RST证据，考虑切到旧H2228独立VXLAN/noNAT（仍须Windows客户端二层入口），不认产品丢包。
- ARM原GoTLS server真正启动后先创建本机真实Linux TUN、双方同时跑独立**真实OS UDP45901**双向应用前置（不是假READY），要求Windows原 \`WBD_WINDOWS_CLIENT_READY\` 和 \`WBD_WINDOWS_OS_APPLIED\`，再用原Win Wintun 10.66.0.2 和远ARM原Rust TUN 10.66.0.1 的TCP45902做4并行连续25s（每流512MiB上限）、160次稀疏回显。所有字节必须由ARM真实原TUN TCP listener核实、Win实际TCP ACK及P99、Windows全机CPU、ARM全机CPU、中继两个方向\`tc\` egress packet和WSL DNAT/SNAT counter与server真实Go/Rust日志同源，不能用Python自身TCP做外层替代。首轮0%损伤有资格才开放双向200ms 1/5% loss FEC2 off/fixed/off；没有本轮真产品通过，不直接改Rust队列。
- ARM原product server保活至**Windows原 GoTLS/Rust owned WAL Stop**的真实客户端结果构件上传才发SIGTERM，由测试netns仅kill自身子进程并还原所有临时网络；拒绝原Windows Stop缺失（\`WBD_WINDOWS_NATIVE_DISCONNECTED_V1\` 和 \`M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS\` 及WAL文件不存在）。独立ARM原服务端退出时也存原日志/actual Stop proof，而不是信模拟标记。两个组必须全部通过；任何错误区分 infra、网络、原客户端与原服务端，保留原始SOURCE/失败，不掩盖。
- 本提交**无Go/Rust生产代码变化，不改 M4、FEC2、默认调度、Windows驱动/Stop**，仅新增四个测量/签名owner测试脚本与CI，扩展既有测试TCP app显式env，仅本H2286角色启用。既有历史测试不受影响。

## 验收条件
产品首次无损0ms正常接通，TCP真实goodput与CPU/GiB和P99/首响应同时报告且两组完成才可标注\`PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP\`。该标记**仍只代表Normal/off上行一个0%工况**，不是“所有平台/所有弱网性能PASS”。若单组底层中继未达800Mbps记网络未合格而非WBD服务能力。针对首轮CPU/P99真实瓶颈才做小增量，例如原GoTLS/Reassembly/NPF raw copy、Rust M4 sendmmsg、方向ACK/SACK和公平调度A/B/A′（逐步保留Stop门），下一步再测原FEC2 1/5%。

\`\`\`feature-impact
{"kind":"none","reason":"H2286 only adds new source-locked real dual Win2025 Npcap/Wintun original GoTLS/Rust → native ARM GoTLS/Rust AF_PACKET/TUN end-to-end diagnostic with exact kernel 443/18727 relays, signed driver and owned Stop verification. App-level TCP duration opt-in, all Go/Rust production source, default, security and Stop unchanged."}
\`\`\`

## H2286 首次真实Runner：先撞上严格构件命名门，不是产品失败
- 精确source \`97db898f3a1fbebcdeea7f2a1b9d9c3dfcd32573\` [Action44936859273](https://github.com/lly8666/wbd-next/actions/runs/44936859273)：7角色中静态门SUCCESS、真正 native ARM64 original GoTLS/Rust＋ISA-L BUILD job SUCCESS（构件 h2286-arm-original-product-97db… 已上传、原Go源码与Rust SHA闭合），Windows a/b 两台真实OS WSL2 Ubuntu成功开机、复用并逐字节核对原Windows Go/Rust EXE/DLL、成功安装签名Npcap1.88和Wintun0.14.1。两组relay也完成源锁通信身份与配置，原Arm server开始真实veth/AF_PACKET。**未得到一个原Windows Client业务测量**，不能给WBD吞吐PASS。
- 第一处明确失败在Windows b\`await_artifact\`：旧H2276的source-locked构件名正则只允许\`h2276-[ab]-(client|relay|server)-(peer|ready|result)\`，拒绝新增的准确合法\`h2286-b-original-arm-product-ready\`，实际抛\`H2276_ARTIFACT_NAME\`；Windows真正NpCap/NAT/GoTLS甚至还未启动。这是助手新增夹具没有扩展原明确allowlist，并非性能缺陷。修复仅额外承认 \`h2286-[ab]-original-arm-product-ready\`，保留原名和强制Run/Group/Source一致性、不会放开任意构件。新单测反例拒绝错组、evil后缀。
- 第二错误在Windows \`if:always()\` 清理中：真实 \`m0_wl_npcap_driver_ci.ps1 -Action Cleanup\` 已输出 \`Npcap...successfully uninstalled\` 和 \`WBD_NPCAP_DRIVER_CI_CLEANUP_PASS\`，但PowerShell\`$LASTEXITCODE\`从helper内部底层命令残留为非零，父workflow误报cleanup失败。修复以**完整exact helper PASS/SKIP回执＋真实Get-Service npcap absent**判定，不屏蔽卸载失败，运行日志仍保存。旧SOURCE失败不涂改。
- 提速：原ARM \`97db...\` 真ISA-L/GoTLS/Rust单次ARM native构件成功，当前修复只改夹具/Action/单测与await allowlist；新Action先\`git diff --name-only 97db..HEAD -- crates r0/go_overlay Cargo.lock Cargo.toml tools/m0_install_public_faketcp.py tools/m0_plan029_linux_dual_native_build.sh\`严格**编译产品输入0变化**才允许从Action44936859273按真实SHA下载/校验同一构件，并原样作为新Action的\`source_sha\`独立manifest provenance上传。新增 \`WBD_H2286_ARM_PRODUCT_FROZEN_SOURCE\`只允许精确 \`97db...\`；ARM native server receipt同时记录运行夹具GITHUB_SHA与原产品编译SHA，不能冒充本次重新编译。两台Windows原始c5066二进制仍用同一更严格的源diff+SHA门。预计之后反复定位NAT/FakeTCP握手，无须每次本机native ARM重新编译。
- 若再失败，优先看原Go client日志的\`WBD_WINDOWS_CLIENT_READY/OS_APPLIED\`和Linux原Go server\`V4_PUBLIC\`，WSL2端原tcp443的PREROUTING/POSTROUTING真实命中数与远ARM原\`wan0\`发包/SYNACK，而非继续运行裸TCP夹具、更不是无测量改Rust队列。新版本只有完整Windows+ARM原业务达到原Stop和ARM真应用字节才开放性能热路径。
