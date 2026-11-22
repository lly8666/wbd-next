# B35｜选中物理DNS IPv4同时服务原Go服务器域名冷引导

## 已发现的具体缺口

B34b (`d70132608bf5`) 同SOURCE [Android dual64 #44978243692](https://github.com/lly8666/wbd-next/actions/runs/44978243692) 11 SUCCESS/4 SKIPPED：原Root App→Go→Rust M4已有可选物理UDP53 IPv4上游；但是原Go `--peer-host` 冷引导仍由固定223.5.5.5上游解析，且App传参只在物理/CN模式发送该配置。LAN-only 网络的本地DNS不一定能访问公网上游；原B28在选中Network的 `getAllByName` 找不到A记录时会交回原Go，旧Go仍固定公网DNS。这是一个真实生产调用链缺口，而不是更换协议或增加系统拦截。

## B35一条垂直接线

- 复用B34的同一已选物理DNS IPv4设置；默认223.5.5.5保持原行为。Root App如果服务器为域名且用户显式填非默认上游，即使App DNS仍选隧道，也向原Go传冷参数，不再先调用Java的网络DNS替代原Go；若服务器为IPv4且未启用物理/CN DNS则不传无用参数。
- 原Go CLI允许非默认上游用于 `--peer-host` 或原有物理/CN DNS。原 `dnsnative` 的Android Bionic `android_setsocknetwork` + `SO_BINDTODEVICE` 原socket拨号不变，只把固定223.5.5.5:53换成同一已验证IPv4:53；有TC标志时原UDP→同端点TCP53，绝不另造DNS worker。
- 同一原Go `bootstrapQuery` / `bootstrapReplyIPv4` /标准FakeTCP/TLS/认证保持原样。仅在连接前冷启动使用，Rust M4应用DNS默认和已接线的Root UID/FIB/Stop都不变。这个TCP53仅是WBD**服务器自身域名**引导，**不是**App TCP53物理转发或系统netd DNS接管。

## 软件验收与未证明

同源Go Host真UDP/TCP53自定义上游/旧默认/无效地址、Java原App argv（选中域名vs IP、隧道DNS不变）、原生产源检查、Android Go/Rust双ABI签名APK及原Linux Server Oracle，以新SOURCE Action为准。本devlog提交时不能预称这些测试PASS。Android实体Network真实查询、系统Resolver、App TCP53物理路径、IPv6/CLAT、Game2/4、热点、切网和吞吐仍为NOT_RUN或MISSING。没有操作个人设备或外网服务器；不动main。
