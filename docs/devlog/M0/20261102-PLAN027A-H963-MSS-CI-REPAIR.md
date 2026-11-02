# PLAN027A H963｜固定MSS现行源码首轮CI错误修复

H962 Go FakeTCP真实SYN/SYNACK字节测试PASS，但[Windows源码编译41472045532](https://github.com/lly8666/wbd-next/actions/runs/41472045532) FAIL：后段 `physical` 将前段真实网卡物理MTU的uint32变量重声明为`PhysicalPath`结构。只把后段物理路由结构命名为`physicalPath`，保留Rust计算的真实物理值、Windows原装配路径并精确重钉plan020单项blob。

[功能目录41472045492](https://github.com/lly8666/wbd-next/actions/runs/41472045492)超过16KiB；只缩略scope描述，保留历史源SHA、证据路径和PASS/FAIL，当前大小14725B。[冻结M4回归41472045542](https://github.com/lly8666/wbd-next/actions/runs/41472045542)仍期望41个operation，但当前M0已合法加入7个FakeTCP MSS覆盖：保留历史M4 34哈希，以及精确48项/11新增路径和操作类型的fail-closed检查，不按旧版本协议保留1360。

H963没有新MSS算法、热路径或历史原生资格。待当前SOURCE编译和原生真实SYN/SYNACK及OS双端读回后才能判MSS修复成功。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Repair H962 Windows compile, historical M4 current exact operation checks, and card size; all feature verifications preserve old source/status."}
```
