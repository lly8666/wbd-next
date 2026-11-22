# B33｜原Android Root普通App最多4网段真实内核直连／分流

基线为实验 `47276e16`，B32a原 Go/Rust Android dual64＋Linux Oracle＋正式ARM64签名APK [#44969771959](https://github.com/lly8666/wbd-next/actions/runs/44969771959) **11 SUCCESS/4 SKIPPED**；治理SUCCESS，不是手机真实网络E2E。

## 完成的实际产品接线

- **原FIB路由主线**：在B31已同源完成单UID、组选UID、all-app共用物理服务器 `throw peer/32`基础上，直接复用真实内核 `ip -4 route add throw CIDR table 19842`，最多4条显式IPv4网段，首条App UID `ip rule`授予前逐条安装/读回。对协议RAW/TUN包不新增任何代码；FIB只让这些目的地继续执行Android后面的系统规则，**不保证一定通过选中物理Network**。默认不配置就是既有全隧道。
- **原Root journal**：原 `Plan`、`GroupPlan`、`AllAppPlan` 增加可选 `direct_cidrs`，旧journal未有此字段仍保持原精确Stop恢复路径；同一 owner flock、原路由表、UID和持久journal。Stop先删UID规则、再删4个显式前缀和已有服务器/32，再删TUN default，读回后才移除journal。只复用现有单一控制面。
- **原Go CLI**：Android限定冷参数 `--android-direct-cidrs`，解析排序与IPv4规范化，只在已经选择单UID／组UID／全App后允许；真实同一 `androidRootRouteAfterNative` 继承 TLS/凭据/自动/32租约/原Rust M4就绪门。非Android原Linux产品仍拒绝Android专属参数。
- **Root正式App**：真实编辑框→Intent→Service冷复核→原Go argv，非密钥设置导出/导入照旧，无热更新；Host JVM运行生产 `RootDirectIPv4` 格式化与 `RootConnectionSettings` 回读，原签名APK源码门检验完整接线。

## 可验证资格与缺口

Go `rootjournal` Host新测试覆盖三种真实原内核命令、安装在UID首规则之前、Stop释放、失败中途回滚、重复/非法CIDR与外来路由冲突。沿用当前已经存在的 Linux Oracle `go test ./internal/v4productcli/rootjournal` 与 Android Java Source门；仅在**本B33 SOURCE** Actions确实成功后声明HOST_PASS/BUILD_PASS。无设备、无用户真实服务器联机授权，Android实体IPv4直连、原业务TCP/UDP双端内容、系统netd DNS、Game2/4、IPv6/CLAT和性能仍NOT_RUN/MISSING，各自分别标记。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B33原Android Root single/group/all三种UID路由支持最多四个用户CIDR真实私有FIB throw、原持久journal/Stop、原Go冷旗和正式Root App/SAF/Host测试完整纵向接线"}
```
