# H1033 PLAN028 — Windows native route/address wake into original TLS Stop/reconnect

One original Windows client cold controller now subscribes to `NotifyRouteChange2` and `NotifyUnicastIpAddressChange` (IPv4), coalesces notifications at 200ms quiet / 500ms absolute, and compares fresh OS physical egress ifindex/source/next hop/interface MTU against its prior readback. Identical effective paths, the owned VPN adapter, and no-physical-path events do not manufacture a reconnect. Callback only sends a 1-slot wake; no TLS/OS work or per-packet FFI executes in it.

After a real changed kernel path, the existing Normal/off/Fixed/Auto or Game2/4 product exits its existing native worker loop, fully joins Rust M4 and restores the original WFP/route/Wintun WAL, then its existing single Go cold supervisor reauthenticates with fresh physical NPF source/interface/next hop and a newly computed native MTU budget. A change during protected TLS/OS Apply prevents publishing stale READY. User Stop stays terminal; no second owner, credential bypass, wire format, FEC or crypto changes. The mode/connection scope remains exact original authenticated TLS.

**Scope**: this is Stop-before-reconnect, NOT an A+B overlapping Windows lane handover. Windows real OS change/driver rebind and seven-mode handover still require physical native qualification. Small Go tests cover coalescing and fingerprint changes. Source verification and Build/Native status belong to same SHA; PLAN028 still IN_PROGRESS.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1033 Windows original protected TLS client now uses native route/IP notifications to enter existing exact Stop then reauth for Normal/FEC/Game without Health90 wait; event coalescing/fingerprint tests."}
```
