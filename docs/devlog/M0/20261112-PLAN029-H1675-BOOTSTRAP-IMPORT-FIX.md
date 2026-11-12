# PLAN029 H1675｜修复 H1674 Windows import 漏项

- H1674 SOURCE 9d214f3 Windows Go源码Action [43220830074](https://github.com/lly8666/wbd-next/actions/runs/43220830074) FAILED，首次错误为 `internal/windowsclient/native_bootstrap_dns_windows.go: undefined: errors/netip/time/context/net/fmt`。WinForms Action [43220830203](https://github.com/lly8666/wbd-next/actions/runs/43220830203) 同源Go编译FAIL；旧M0-WIN-LINUX Windows编译亦FAIL，同源根因。是H1674重写文件头注释时移除import，不是 DNS 物理网络失败。
- H1675原样补回该文件原来用到的 Go Windows imports，保留单dns.direct选路和唯一物理NPF查询。manifest result_blob 精确同步。失败原始Actions保留，不刷 seed；当前源码未取得新 Windows compile PASS前不能提升验证等级。
- 原H1672签名Wintun TCP内核SYNACK缺失仍FAIL/根因未知，与该静态编译漏项相互独立。无旧WFP的新四stage产品和Rust实网IP+域名分流仍OPEN。

```feature-impact
{"kind":"updated","ids":["client-domain-bootstrap"],"reason":"Fix H1674 original Windows Go source missing imports after bounded physical DNS bootstrap change; preserve failing SOURCE and validate next Action."}
```
