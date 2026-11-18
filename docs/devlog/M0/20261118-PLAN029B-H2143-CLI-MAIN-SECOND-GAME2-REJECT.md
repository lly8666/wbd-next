# H2143｜原 Windows CLI 第二道 Game2 CN 分流拒绝首错

[Game2 Action44219372574](https://github.com/lly8666/wbd-next/actions/runs/44219372574) SOURCE `4edab359e7af6e38d35fe4ee6944bd1ef49ec0db` cheap/WinGo/WinRust/LinuxRust/双端原构建PASS，但**native Action FAIL**，真正 Windows exe CLI 2秒前TLS直接 `PLAN029 CN split Game2 not wired; select Normal or Game4 (four lanes)`。原ZIP `14389689283` sha256 `32434edacd97f508045c344aff14f74d0ca2641fcb210d600f72ebcf14e98a96` 21成员CRC全PASS，证明不是网络方向或Rust失效；业务/OS应用 NOT_RUN。

H2139已删除`runM0NativeV4Windows`入口旧拒绝，但安装清单对**原 Go `cmd/wbd-client/main_windows.go` 的replace patch**仍注入完全独立的CLI早拒绝。此提交仅从 `r0/go_overlay/assembly/manifest-plan020-m0.json` 删除那条旧补丁并将原构建真实生成的源码blob `58790a... `经严格单行移除后重新 Git blob pin为 `e9478ad94fff3942155c20795bc2636dd9e233f7`。该变更放行 Game2 与原Game4共用认证Cold V4，但仍保留CN绝对规则、Direct容量、公共DNS和Rust Owner/OS Stop全闸；非改Go私有热路径、FEC/AEAD/repair/wire。下轮只补Game2原生重验，未实测不晋级。

```feature-impact
{"kind":"none","ids":[],"reason":"Remove obsolete original-Go CLI Game2 early rejection injected by the frozen manifest after already wired original Game2/4 Rust V4 owner; no new feature contract or hot-path change."}
```
