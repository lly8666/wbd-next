# A2 第一批｜Android/Bionic 真 RAW 收发 FD 与物理网络强绑定

SOURCE：本次提交 SHA 以 GitHub commit 为准；提交前未声称测试通过。起点远端 Android \`0e1fe307125b17f7edbc66ac4d16b6249c743b39\`，main \`fb24fe784d960e3e8bf4ca63cc2a22332247e1dd\`。本批仅限实验分支；无 worktree，未检查远端不存在的本地未提交文件。

- 在已有 \`android_root_io\` 中新增 Bionic 内核 RAW **实际** TX/RX FD 原语（非模拟包、非协议替身），不改标准 Go TLS/认证/租约及 Rust PN/FEC/retransmission。RX 按已经认证的对端原四元组安装与 Linux M4 同语义的13条 classic BPF，失败即关闭 FD，不降级为无过滤监听；返回的原始字节仍为 **未认证**，必须由同一原 Rust M3 解析/AEAD/重放门处理。
- RAW TX 仅在原Go冷控制传入明确 physical Android \`Network\`、接口、ifindex、MTU、generation 和外层源/目标 IPv4 后打开，\`android_setsocknetwork\` + \`SO_BINDTODEVICE\` 双绑定、\`SIOCGIFMTU\` readback；使用内核 \`IP_HDRINCL\` \`sendto\`，原Rust拥有完整不可变外层 IPv4/TCP DATA 与共享MTU快照。绝不把 Go/Java/JNI 放在逐包路径，不建新的重传器或 TLS。
- FD RAII 保证初始化任意失败关闭；Stop 标记阻止新调用。**尚未接入原M4线程 join / BorrowFence**，因此不可声称完整 owned Stop、p99、真实TCP/UDP。
- NDK C gate 同时验证 Bionic \`SIOCGIFMTU\`、classic BPF 布局及 option。保留 A1 独立双 ABI 和故意不能绕过的原Go真实 M4 全链接门，不新增 synthetic PASS/探针按钮。

**测试：** 原代码和ABI本轮提交后由 SOURCE 对应的唯一 Android product 构建 Action 决定，提交前一律 \`NOT_RUN\`。Android16 KSU↔同源真实Linux WBD、TLS/认证/租约/TCP/UDP/16KiB真机装载/网络变更/ISA均 **NOT_RUN**。旧 A1 \`c385502a\` Action44015392698 的冷ABI BUILD_PASS、完整Go M4链接 FAIL 继续保留，不能覆盖。

**唯一下一步：** 对照 \`v4_embedded_go.rs\` 原 \`ScopedRawIpv4Tx/Rx\`、\`ScopedTunSink\`、\`ScopedRouteBudget\` 和全部 Go CGo M4 调用，把这些 Bionic FD/网络预算操作纳入**同一**成熟 M4 worker与同步 Stop，并在原Go完整产品全链接门实证；之后 A3 才开始同源真实 Linux server 连接。

\`\`\`feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A2首个原生I/O施工切片，Android内核RAW TX/RX四元组过滤、特定Network/MTU/代际强绑定与NDK ABI门；尚未M4接线及真实业务测试。"}
\`\`\`
