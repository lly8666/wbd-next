# B124b｜真实 CA 与完整备份 UI 读回

B124a SOURCE `d71c557cb7578739fb9ab10f7b570bcdce3a1c4b` [Action 45659951126](https://github.com/lly8666/wbd-next/actions/runs/45659951126) 14 SUCCESS/2 FAIL/8 SKIPPED。[ARM64 APK及源码检查](https://github.com/lly8666/wbd-next/actions/runs/45659951126/job/139369180787) PASS；[Normal](https://github.com/lly8666/wbd-next/actions/runs/45659951126/job/139370369188) 原RAW SYN/SYNACK、TLS/lease、M4普通App TCP/UDP、owned Stop PASS；[BPF独立内核夹具](https://github.com/lly8666/wbd-next/actions/runs/45659951126/job/139370369191) 真实detach/reattach/restore PASS，非实体热点。API35/36均在CA导入状态提示“已导入 1 张证书”定位失败，第一槽尚未完成保存。实际CA字段未读回，不能断言导入业务失败。API35 artifact 15044917029 核验 ordinary UID socket PASS。两治理Action仍独立失败，功能卡大小检查及121单测已经过，不改M0 cursor/evidence。

本轮只改真实UI测试：系统文件选择后确认返回原App，读取实际CA输入框（XML换行归一），导出按实际WBPC文件读取，恢复按已删除槽位真实重新出现及后续载入/再导出字段相等判定；保留密码、RouteKey、CA原字节比较。失败时保留CI专用临时测试界面截图。生产Java、原Go/Rust、协议、路由、数据面完全不改，不增加防御门或后台轮询。只用已有B115 marker触发API35/36 UI及既有基础构建，不重跑Normal/BPF/七模式guest。新SOURCE待CI。ARM64实体和真实性能未验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Qualify complete server profile UI using actual CA field and backup file readback; preserve B124a original Normal and BPF receipts."}
```
