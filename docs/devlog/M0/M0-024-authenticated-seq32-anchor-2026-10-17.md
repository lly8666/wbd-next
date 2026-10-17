# M0-024：受保护原路径 seq32 长跑可信锚点（2026-10-17）

- **why_now**：当前main已有原Go TLS凭证→Rust owner→Linux raw/TUN的持续双向业务与同VM P10；但原`background_raw_once`每DATA把wire seq32相对固定Go bootstrap `rx_boundary:u32`扩展。长期运行超过约半个32位序号空间后，合法后继DATA可能被错误延伸/拒绝（不能归因旧80秒中断）。属于024真实热路径的正确性安全栅栏，不是重开已完成CPU优化。
- **实质源码**：只改M0的`crates/wbd-engine/src/v4_embedded_go.rs`。新增单session `rx_seq_anchor:u64`、初始可信Go boundary；M4原tuple/checksum验证和`extend_seq32`仅形成候选；仅当原M3 AEAD+PN去重的`AuthenticatedRxReport.link_ready==1`时推进高水位，不由未认证TCP头、重复、无效LINK或失败seal推进。Stop/rotation新Entry独立，不新建session/worker；移动参考不追旧包，不因旧洞等待fresh。64位加法溢出明确失败。
- **精确验证**：新增同一生产辅助函数的seq32回绕、半空间固定boundary误扩展、认证成功/失败、重复和溢出向量。原`m0-v4-native-owner-probe.yml`、`native-regression.yml`及真实Go/Rust/Linux raw/TUN功能Actions应由此源码push触发；尚未观察run/manifest的部分为PENDING/NOT_RUN，不能以单元向量代产品PASS。相关§4 I01–I04；长业务/真实高带宽跨回绕仍NOT_RUN，500Mbps/80秒症状不作归因。
- **边界**：不改worker M1/M2/M3/M4源、生产features、Go ABI或外部机器；原配对P10的CPU正负反转INCONCLUSIVE、D10 ptrace失败和原023/超MTU开放。
- **next_action**：核对本次代码SOURCE Actions和artifact后，继续024方向-owned TX/RX真实接线/Stop-fence与ready聚合，不把修复扩展为未经证实的性能收益。
