# B65 — Android software tether IPv4

- Opt-in existing active Android 16 downstream selection via public TetheringManager callback; no hotspot creation or hidden API.
- Original authenticated TUN lease, separate table 19844 / rules 9580–9581, scoped FORWARD and SNAT to lease. Native M4 remains the sole data plane.
- Downstream loss requests original Stop. Settings retain opt-in only, not an old interface index. Cold reconnect must revalidate.
- Software forwarding only: requires ip_forward enabled by Android, hardware offload explicitly disabled and BPF offload inactive. No global setting or BPF map mutation. No hotspot system-resolver capture or IPv6 qualification.
- Exact journal cleanup and host command seam test; actual Android hotspot packets NOT_RUN. No claim of general tethering/offload compatibility.

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B65软件热点/USB IPv4内核转发、SNAT、活动下游选择与原M4 Stop/Restore、四槽设置接线；offload兼容及实体未验。"}
```
