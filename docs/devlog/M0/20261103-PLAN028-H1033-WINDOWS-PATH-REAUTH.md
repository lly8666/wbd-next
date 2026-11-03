# H1033 PLAN028 — Windows native route/address wake into original TLS Stop/reconnect

One original Windows client cold controller now subscribes to `NotifyRouteChange2` and `NotifyUnicastIpAddressChange` (IPv4), coalesces notifications at 200ms quiet / 500ms absolute, and compares fresh OS physical egress ifindex/source/next hop/interface MTU against its prior readback. Identical effective paths, the owned VPN adapter, and no-physical-path events do not manufacture a reconnect. Callback only sends a 1-slot wake; no TLS/OS work or per-packet FFI executes in it.

After a real changed kernel path, the existing Normal/off/Fixed/Auto or Game2/4 product exits its existing native worker loop, fully joins Rust M4 and restores the original WFP/route/Wintun WAL, then its existing single Go cold supervisor reauthenticates with fresh physical NPF source/interface/next hop and a newly computed native MTU budget. A change during protected TLS/OS Apply prevents publishing stale READY. User Stop stays terminal; no second owner, credential bypass, wire format, FEC or crypto changes. The mode/connection scope remains exact original authenticated TLS.

**Scope**: this is Stop-before-reconnect, NOT an A+B overlapping Windows lane handover. Windows real OS change/driver rebind and seven-mode handover still require physical native qualification. Small Go tests cover coalescing and fingerprint changes. Source verification and Build/Native status belong to same SHA; PLAN028 still IN_PROGRESS.

## Small same-source check

Windows original-Go product and test compile plus the 200/500ms and physical route fingerprint Go units PASS on SHA `ef313bfee89a6519245ed79ca8a4e70a14f7c665`, Action [41619392833](https://github.com/lly8666/wbd-next/actions/runs/41619392833), Windows Go preflight job `125861145324`. Original Windows signed native OS/WAL regression for unchanged code SOURCE `9efba909eeec57d483eca99439a27d56f6fdcc45` Action [41618704334](https://github.com/lly8666/wbd-next/actions/runs/41618704334) SUCCESS. No real physical path-switch event/lease overlap test is claimed.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1033 Windows original protected TLS client now uses native route/IP notifications to enter existing exact Stop then reauth for Normal/FEC/Game without Health90 wait; event coalescing/fingerprint tests."}
```
