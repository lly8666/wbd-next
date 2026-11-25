# B119｜真机 Root 启动与域名引导，冻结共享数据面

用户补充B117 `70fb497b424fd36ec1ed168981710a596377191f` 更换域名为IP后本机连接及Wi-Fi热点下游经WBD实际可用（用户报告，USB/性能未验）。B118a `a34649ac1b6bab701619af04f43adffe33992e90` API36 TXT四次均到ROOT_GRANT_REQUESTED后约2ms ROOT_LAUNCH_FAILED，未见ROOT_PROCESS_LAUNCHED/Go入口；旧报告未分Java argv异常与exec su IOException，不得归因BPF或DNS。每次CI debug APK使用一次性签名，重新安装后KernelSU授权/可见性值得核查，不假定已证。

B119仅App冷启动：默认物理DNS的服务器域名在选中Android Network解析IPv4（不再仅未验证LAN），成功按原--peer-ip进入Go，保留SNI、显式自定义物理DNS及原Go无A记录fallback。将原命令构造和su启动异常区分，固定errno类及界面提示；无新增安全门、不改Root授权或尝试绕过。B118a选定下游上行BPF及原内核FIB/SNAT保持原样，本次无Go/Rust/系统路由修改。

B118a Action 45616834899 Normal及BPF kernel PASS；ARM64实际APK已生成但旧Game UI源码断言FAIL，API35/36旧保存成功文案断言FAIL；修UI文案与源码断言，不重跑七模式。B119实际ARM64运行、域名业务、共享仍待验；PR36 Draft。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Selected Network hostname bootstrap and distinct argv/su launch errors; preserve scoped sharing and fix UI test mismatch."}
```
