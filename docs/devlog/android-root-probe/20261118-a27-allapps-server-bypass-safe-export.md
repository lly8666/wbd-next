# A27 — 默认普通 App IPv4、服务器 IP 避免回环与脱敏导出

本轮只检查/施工，不运行模拟网卡绑定或真机，不碰用户服务器。原 APK 默认 all-app 勾选为 true，但仅对20用户空间普通AppID10000–19999的IPv4设置私有 UID rule，排除应用本身和已知KernelSU Manager；没有系统/root/IPv6/系统DNS/热点全流量接管。此前 WBD 原 Go root UID不被选中，但缺目的服务器IP旁路保护。

原 Go 的全 App 路由方案改为取解析后的真正服务器IPv4，在私有 table19842 首先给原 TUN default，添加并严格读回 server IPv4/32 throw，再逐个安装 UID rule；失败立即精确回滚，Stop 精确清理，原 v3 journal 仅可在相同所有者下恢复为 v4。不能把 throw 视为已验证真实 Android netd 物理出口；手选单/多 App UID 保留原旧路径并明确不宣称拥有同一例外。

正式 APK 增加导出脱敏排障TXT按钮：Android SAF文件保存器、无需 Root/联网，固定枚举Root/原Go阶段码+毫秒时戳、源SHA/API、当前会话阶段与私有FIB旁路读回，拒绝任意原 stdout/logcat、IP、账号、密钥、UID/包名、原始root journal。阶段分类前置 Root Manager/Network、su/SELinux/ELF、TUN/RAW/SYNACK、TLS租约、M4/UID及Stop，方便首个真机故障缩小范围。Host Java测试报告轮转与恶意文本过滤；Go Host测试 /32 异常/外来规则/Stop/旧日志，签名APK含生产同一个导出类。

代码与Actions需同新SOURCE取得结果；编译/Host通过不等 Android真机任何功能通过。Draft PR #36、实验分支唯一；main/M0与用户设备不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"核对默认仅普通App IPv4，原Go全App服务器IP/32私有FIB例外与旧journal清理，新增APK内严格白名单脱敏TXT导出供未来真机高效排查。"}
```
