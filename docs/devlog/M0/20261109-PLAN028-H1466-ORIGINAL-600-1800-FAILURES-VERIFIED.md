# PLAN028 H1466：两场五客户端真实600/1800秒完整产物最终源锁复审

产品 SOURCE `66fb6b4454b1ce4297ab04efa20c7f931ff12383` 一份固定Go/Rust/ISA-L二进制，[原生Action42578056120](https://github.com/lly8666/wbd-next/actions/runs/42578056120) 已实测真正600s和1800s，两台独立x86 Linux宿主，五个真实授权客户端、同一真实Go TLS443/Rust M4服务器和每场全部六份原始Stop。两个产品负载场 CI FAILURE，不能被独立复审Action的绿色覆盖。

600秒：Alice负载真实25→50→75→50 Mbps，真实峰值持续90s，0%物理配置丢包，75M峰值下行UDP唯一包缺**32**（其余阶段0），原server独立每租约`downstream_full=120`、`pending_overflow=45`（8包上限）。更强的源码内部一致性：原server TUN `offered=4776424`、原Alice客户端M3 `tun_delivered=4776379`，两者精确差45，与真实server队列溢出45吻合。此版本>=6/8优先批量老包修复候选仍然失败，该路径未完成故障闭环。

1800秒：五个模式真实混合0/1/5/15/30% netem，原五客户端M4全部换代`PASS_ALL_FIVE_SCOPED`、Alice 24代READY/23次准确旧Stop、六个最终Stop、server全部五租约队列溢出0。但Alice原配置0%物理丢包下行UDP唯一包真实缺**351**，按五阶段分别0/22/142/118/69；原server Alice TUN offer3499378、原Alice M3 `tun_delivered=3498919`，差459包，并非先前相同队列溢出。M3原始计数与应用缺包不必一比一映射；具体丢弃点待原raw transport/轮换与内核收包对照。生命周期`PASS_SCOPED`，零损可靠性`FAIL_SCOPED`，不可汇总成全过。

H1461原 Python H1274 在`phases=[]`覆盖`phase_specs`使全部分阶段信息变空，导致600s新审计误把十条方向都标为NO_GENUINE_UDP、1800s审计`stages[-1]`报IndexError；真实业务文件并未空。现在仅在新审计SOURCE `87cfe4e1f5d832a16e2925f1e90be151a7ad0b19` 修正变量并从不变原始ZIP回放。[纯离线Action42584453380](https://github.com/lly8666/wbd-next/actions/runs/42584453380) SUCCESS、[产物13658711312](https://github.com/lly8666/wbd-next/actions/runs/42584453380/artifacts/13658711312) CRC_PASS SHA256 `e699eaff0d3b0fe54a4b2b4cda01b2681e8e90e044e7884f4fe66227b45d1c40`，六项离线单元、两场真实五用户各10个完整方向5阶段、原始六Stop重验通过，正确复现600的32/45和1800的351/0。两个源必须分别留存，不冒充修复后产品重跑。

下一步分两个故障域做短定向源锁差分：75Mbps集中测原server per-lease SyncSender64槽持满时间、M1原worker取走及发送节律、CPU每核；1800优先对零损Alice每次真实轮换时原server offer、client raw RX/M3、旧代Grace与M4 Commit统计作前后定量对应。不再只盲加共享队列或重复30分钟。旧SOURCE548 Normal75 28缺包/overflow5 FAIL、H998 live MTU FAIL、Android/物理 NOT_RUN、Windows Wintun原1800 L3 NOT_QUALIFIED，ARM64 eef2两条原1800 PASS_SCOPED、Windows600 PASS_SCOPED均严格保留。PLAN028 IN_PROGRESS，未开PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Only original two five-client source-locked stress artifacts and offline rejudge governance; no product code or new native run."}
```
