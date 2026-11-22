# B30｜盘点上位施工进度、标记真实缺口、主线批量推进

对照实验分支 `f115ab1840f1c50eb1922f9c34b67267ca1fd770`，原Go/Rust/Root App/Rootjournal源码、B1–B29阶段记录和同SOURCE [dual64 #44967461025](https://github.com/lly8666/wbd-next/actions/runs/44967461025) 11 SUCCESS/4 SKIPPED。已确认Normal/off、Fixed/Auto/FEC2、TUN App UDP53三模式、LAN引导、完整Root App、原native Stop皆已有产品接线；仍不能把源码Build或旧M4计数写成完整物理TCP/UDP E2E。台账见 [ANDROID_ROOT_IMPLEMENTATION_BOARD](../../plans/ANDROID_ROOT_IMPLEMENTATION_BOARD.md)。

本批主线不做伪Game开关、不写第二个DNS/Go包引擎，先修 Android rootjournal 三种UID范围的真实FIB server peer排除不一致：all-app已有私有table `throw peer/32`；selected/group缺少，导致对应App对同一物理WBD服务端IPv4仍命中TUN默认路由。按已有原root owner+恢复机制补齐，原有Host和同源build验证后再更新台账。手机与服务端未经授权不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B30以源码与同SOURCE Actions标记已施工能力、未验能力和真正MISSING；后续继续原Root UID路由Server-IP例外跨模式闭环，不新增防御/代理框架"}
```

## B31｜真实生产代码：三种普通App UID路由的一致服务端IPv4例外

B30盘点确认 all-app 私有 FIB table 19842 已有`throw peer/32`，但single与2–8UID组同样走default TUN时没有例外，选定App访问自身WBD服务器物理IPv4会再被导入TUN。本轮不另造网络代理：完全复用原rootjournal的`peerThrowArgs`及`allAppRouteState`，在单UID/组UID持久journal上加入可选ServerIP字段（历史v1/v2仍可恢复），原Go TLS后真实`c.peerIP`传入；在首条UID规则前安装/读回内核`throw <peer>/32`，原Stop与crash recovery按UID、例外、default TUN顺序撤回。原 all-app 未改。

既有Go Host fake ip测试覆盖单/组选定App的插入顺序、Stop无残留、失败回滚与外来例外拒删；将整套rootjournal Go测试放入已有Linux Oracle脚本，不造额外重型工作流。Host/BUILD按本SOURCE Actions，真实Android netd下App直连仍NOT_RUN；这不等于物理TCP53或用户自定义直连CIDR已接。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B31单UID与多UID组在同一原Root journal/FIB中复用既有all-app服务端/32 throw，实现三种普通App UID路由范围的物理WBD服务端例外、精确Stop及Host回归"}
```

## B32｜批量真实日常功能：当前用户全部已安装普通App可选

审计证实B26原 `InstalledAppCatalog.visibleNames` 只枚举 `MAIN/LAUNCHER`、text/plain SEND、HTTPS VIEW，目标游戏/普通App即使安装也可能完全没有这些入口。原Root APK正式App picker现在申请 Android `QUERY_ALL_PACKAGES`（该Root工具为自签名侧载测试APK，并非商店上架方案），通过同一 `PackageManager.getInstalledApplications(0)` 冷获取当前用户App包名；保留旧三Intent supplement，不得手填凭空UID。原 `InstalledAppTarget.eligible` 过滤系统/root和WBD自身不变，`stillSameGroup`和`stillSame`在Service和root su前仍以当前包名→真实UID复核，同原Go路由最大8 UID /16包。既有UI筛选/批选/SAF持久化不改，无任何Go/Rust每DATA处理或新后台线程。旧B24/B26/A7的窄包可见性描述保留为历史阶段，README以B32为当前模式。

实证层级：Host App源码门必须核对 manifest 权限、真实PackageManager枚举、UID复核；正式签名APK从原Android产品SOURCE编译。新SOURCE未验前只记WIRED_CANDIDATE，实机包列表/Android UID路由、Game应用E2E均NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B32 Root App枚举当前用户全部已安装普通App及无launcher游戏，用现有PackageManager身份复核与原UID路由；保留旧筛选/批选/SAF，不新建控制器或逐包处理"}
```

## B32a｜正式APK构建门的旧窄包权限假设

B32正式Root App现从PackageManager冷枚举全部当前用户普通安装包，原sideload Manifest有`QUERY_ALL_PACKAGES`。但 `android/root-app/ci/build-source-locked.sh` 历史B26静态检查仍断言该权限不存在，和已改真实产品行为冲突。B32a只将这个signed APK Manifest门改为确认权限存在，原 `AllAppRouteScope` 注释对齐当前行为，不动原Go/Rust/TUN、Root同代UID路由和Stop。B32旧SOURCE如果因此FAIL，保留真实失败；B32a新SOURCE必须同源双ABI、正式APK及Linux Oracle通过才称BUILD_PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B32a将正式签名APK B26遗留 narrow-manifest source gate改为B32当前普通安装App可见性；Go/Rust与原Uid内核转发均不变"}
```
