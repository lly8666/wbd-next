# PLAN029 H1714｜收H1713真CN DNS53→持久FakeIP→业务UDP；解除no-WFP正式入口死循环

- 收 [H1713 Action43368431989](https://github.com/lly8666/wbd-next/actions/runs/43368431989) SOURCE 3bb00716252435ab2579a5cd786696256c43bf55 Windows2025 **SUCCESS**，原始日志首到路径：原Windows应用UDP/53查询 www.cn.example→签名Wintun唯一Rust RX→物理绑定单Direct DNS socket至独立Ubuntu WSL2 Linux 172.24.31.186→CNAME/A真实解析→写入并同步92B portable FakeIP文件→Windows应用收到A=198.18.0.1 TTL30→真实Windows应用请求该FakeIP业务UDP→Rust替换真实guest IP经物理源172.24.16.1 ifindex22发往Linux→Rust逆向Wintun回包、应用真实收到。单owned HyperV guest规则Stop已准确删除。该能力门是显式m0_v4_probe，**不代表原TLS Normal/Game4、强制Tunnel DNS、共享海外CDN反例和外部物理互联网产品已经通过**。
- 另收目前main若干历史正常CI依旧FAIL：original M0-WIN-LINUX/旧Rust owner ABI/cross-ABI及PLAN012组合与新的029探针场景不同。保留原结论，不因H1713单Action绿而宣布没任务，也不派发028旧矩阵。
- H1697已真实证明四个Win32 no-old-WFP OS writer能Apply/readback/准确Stop；但正式N4PrepareRealWindowsProduct仍因为`assemblyOnly`无条件拒绝。H1714只在同一个真实`N4OriginalCurrentPinnedWintunIdentity`、原TLS/Rust owner验证+exclusive `BindOriginalNativePacketRing`成功**之后**，要求`lease/mtu/dns/routes`四个确切Windows stage类型与共同WALPath、没有第五guard、DNS单地址；再次验证原auth owner，然后解除一次性装配标记，交给现有controller.Connect执行真实OS操作、真实first/reverse、OS Applied读回。没有no-op WFP、没有历史绿色票授权Applied。失败先Drain当前Rust借用再Kernel Stop，不丢持有中的ring。原read-only预检`Ready=false`不变，但移除错误的“4stage未验无法执行”文本，改为“只读检查无法观察当前authenticated owner/Applied receipt”。
- 对应Go pure test覆盖假stage被拒、认证proof失败不得lift、第五guard拒绝、四真stage类型cold unlock一次性、无OS setter或WAL写入；**H1714代码截至提交只写好，Windows编译与真实产品Apply仍 NOT_RUN**。本次更新四个Go overlay真实blob及assembly manifest hash，不放宽原始冻结donor SHA门。
- 接下来分开推进：严格SOURCE构建/原TestPlan029夹具；正式唯一Rust Wintun Normal/Game4双方向DNS及Direct TCP/UDP装配、非CN海外共享CDN实证、owned Stop/IPv6/GUI/padding和D1–D5/P1–P2，029仍IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["windows-network-wal","dns-split-ipv6"],"reason":"Collect genuine H1713 signed Wintun CN DNS53 direct+CNAME/journaled FakeIP+app UDP reverse PASS, and source-stage current-TLS-owner-gated four concrete no-old-WFP OS product admission instead of circular assemblyOnly refusal."}
```
