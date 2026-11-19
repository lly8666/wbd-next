# H2172｜PLAN029 Linux x86_64/ARM64 真实双端首轮夹具首错修复

H2171 [Action44254638755](https://github.com/lly8666/wbd-next/actions/runs/44254638755) 两台native x86_64与native aarch64 hosted Linux OS（没有QEMU）同SOURCE `c3fba1ed215a4191e2244621adeeb195303542df` 都完成原Go TLS CLI客户端+服务端、Rust+ISA-L真实编译、完整二进制 SHA256、Go/Rust定向单测PASS；但**两端CI均FAIL**，只运行首个Normal，不把编译当成实网PASS。

下载原始Action artifact `14405906445` x86显示 `app-c2s-listener.log` 真实Linux UDP接收+echo和TCP接收+echo全部有 PASS。x86 app sender在`TCP.shutdown(SHUT_WR)`并收到数据/对端FIN后才调用`getpeername()`，Linux返回`ENOTCONN`；由于逻辑`bytes(data)!=reply or getpeername()`短路条件，能触发该异常证明bytes回传已经精确相等，是**夹具误判**，不是数据面FAIL。将真实peer校验移到`connect`后立即执行，收到echo后只校验完整bytes；仍保留Linux原内核IP及数据校验。

下载 artifact `14404988800` ARM64的`app-c2s-listener.log`已打印`PLAN029_LINUX_APP_SOCKET_READY c2s`，而shell却报`LISTENER_NOT_READY`。根因新探针在sudo/ip-netns短生命周期包装PID退出时过早跳出readiness循环；Python实际listener已有绑定。仅去掉这段非产品PID推测，保留70×100ms有界真实socket READY标记以及listener真正完成后`wait`、UDP/TCP真实回包检验；未假写READY或补“成功”标记。

加入静态回归测试，检查两原生ISA、五scoped原Go/Rust模式、实际内核socket、原helper/签名约束和两个首错不会复活。**没有产品Go/Rust加密/网络逻辑更改，没有降低Linux双向UDP/TCP/MTU1460/FEC/Stop硬门**。新H2172 Action双真实Linux native验证结果未定，后续按真实证据追加，不借旧H2171的失败日志升格。历史旧冻结ARM64 workflow44254639335下载原archive404单列，非这次Linux双架构业务FAIL。029/029B完整技术仍OPEN；030不开始。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct two first-fault native Linux dual-ISA application fixture false negatives (TCP getpeername after FIN and sudo wrapper readiness); add explicit regression checks, no product changes or scope downgrade."}
```
