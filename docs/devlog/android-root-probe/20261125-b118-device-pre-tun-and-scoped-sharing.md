# B118｜真机冷启动回归、共享入口缩小与 UI

用户B117/API36收据 SOURCE `70fb497b424fd36ec1ed168981710a596377191f`：六次完整START均到原Go INTERFACE_FOUND 后 exit1，未到TUN/RAW/SYN，无共享故障枚举。报告不含实际Go错误、是否勾选共享和具体网络/配置，不能断言唯一根因。用户明确勾选/取消共享均不能连接。B117 CI Normal及独立BPF fixture PASS不是该设备PASS。

Go只在域名引导真实需要时在SYN前构造物理DNS dialer；字面IPv4不被无关Go DNS scope挡住。实际物理/CN Go DNS relay于原认证后需要时构造，原Rust/RAW/TLS/认证/MTU不变；冷失败标识实际失败的NETWORK/MODE/CLAT/PHYSICAL_DNS/BOOTSTRAP_DNS/CLAT_ROUTE/MTU。无新增逐包工作或安全门。

共享仍复用原TUN、内核 iif 私有FIB/SNAT/DNS路径，BPF只处理选中下游的上行 ingress（无挂钩不强制摘除），保留物理上游回程及其他网卡BPF，不再以全机XDP状态阻断；监听仅选定下游，旧B117 journal按原接口归还。硬件HAL独立，已运行HAL不能凭settings写入宣称已停。新方法是候选，实体Wi-Fi/USB及当前手机连接仍待验。

App：关闭程序先取消自动恢复并请求原Stop，owner结束后退出task；Fixed才显示FEC档位和真实比例；全部保存按钮移到设置尾部、显示完整保存含义；共享网卡显式刷新注册。复用原完整SettingsStore及10槽。不擅自终止系统进程或操作实体机。

B118a同步真实UI脚本到新按钮名称，实际设置MTU与Health后重启读回、空闲关闭与重开；删已不调用的全机XDP检查实现。新SOURCE待Actions：复用B117普通真实远端与Android真实BPF fixture，验证保留非选中挂钩；ARM64签名APK、API35/36 UI。实体共享及普通真机回归 NOT_RUN；main不改，PR36 Draft。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Device pre-TUN failure, optional DNS cold dependency removal, selected downstream only sharing and settings/exit/FEC/refresh UI."}
```
