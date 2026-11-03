# H1007｜PLAN028真实双端认证/自动租约连接：首个成组代码SOURCE

2026-11-03：在H1004 A+B代际fence真实Go TLS 20/20源锁通过之后，沿PLAN028§0.2继续施工。**本批是一次性写齐Go admission + Linux client/server Normal/Game + CLI选项 + TLS/配置夹具的产品候选，不是已通过的多客户端原生产品。**

## 本SOURCE写了什么

- 复用固定老版 `logicaltunnel.DerivedTunnelID / ResolveInstallation / LeaseRegistry`：客户端 `--auto-ip` 自动持久化安装ID（仅0600 ID文件，不持久化IP），每账号+安装派生稳定16B tunnel；同一账号的两个设备互不覆盖。原手动`--tunnel-id`保留，auto场景拒绝伪造手动ID。
- 原V4 protected TLS的`V4ServerOptions.Authenticate`回调可使用`--users-file`只读0600账号表；先真实TLS识别、解密认证请求，认证成功后才可epoch.prepare和`V4AllocateAutomaticLease`。不把用户名/源IP/NAT当认证；不动旧Go TLS/marker算法。
- 原V4 `AutoLease/InstallationID` wire扩展既已存在，直接重用；`V4AllocateAutomaticLease`严格校验安装ID、账号派生TunnelID与旧分配器返回的/32。客户端`AuthenticatedLeaseIPv4`冻结已保护回复，防调用方篡改`Negotiated.Lease4`后篡改OS地址。
- Linux Normal和Game在真实受保护回复到达后，Rust开始真实M4 TUN读取**之前**安装/读回有效IPv4 /32；Game所有lane回包必须是同一设备同一IP。单程序整个生命周期共用epoch store和7天租约表，回收前查询active/pending，不可第7天回收活跃IP。server TUN本地地址必须与客户端pool错开且路由前缀覆盖pool。
- 默认用户outer MTU 1460、不含L2，手动outer 1500最大值和Rust MTU预算/OS读回不变。额外Go TEST：三组真实TLS账号+设备分离、错误密码、跨账号伪造ID、原IP续租、新TLS epoch、错误客户端Lease4突变；CLI单元验证0600凭据/安装、server pool覆盖/不吞本机地址、auto默认值。

## 尚未开放的产品边界

- 当前服务端仍只有一个native Rust shared I/O owner，Go一个server实例仅接受一个业务session；Game仍多监听端口。不能因为多个TLS会话单元验证通过而声称同端口并发业务或7模式A→A+B→B。
- Rust共享TUN单reader、按client /32 O(1)出站分发及按五元组入站分发尚待下一完整工作包接通。旧/新native owner并存开关**保持关闭**，避免多线程争读同一TUN；设备租约异步续接真正业务尚未证明。
- 原借站marker在首次TLS前依赖route-key；本批保留手工密钥与recognition，没有用TLS后导出/公开常量冒充账号密码UX完成。Windows原生变网通知、Android真机、物理在线MTU缩窄仍待后续；H998失败原样有效。
- 客户端使用自动IP时临时TUN地址在TLS前为169.254.240.1/32，必须在原Go认证/OS安装后才启动Rust；服务端lease pool路由不能包含本机TUN地址。实际网测不得将此占位地址当有效租约。

SOURCE提交后自动编译/原生Action按精确SHA收集；无新的ACTION结论前全部`IMPLEMENTED_NOT_TESTED`，不拿旧SOURCE PASS代替。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"PLAN028 protected multi-account account roster, pinned original installation/lease reuse, exact server/client Normal/Game cold IPv4 OS application and tests changed; shared Rust single-port business remains NOT_RUN."}
```
