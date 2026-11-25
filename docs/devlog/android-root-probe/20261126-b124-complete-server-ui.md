# B124 — daily Android UI and complete server profiles

User requests concise UI, single full server save, portable export of password/key/CA, retire early device debug. Keep original seven mode values, flags, TLS behavior, Root scope, DNS modes, B123 IPv4-only sharing, and Go/Rust unchanged.

UI: Home connect/stop/exit, saved server choice, network and mode; Server page named slots, fields, CA and backup; Apps scope, DNS/routing; Settings MTU, keepalive, tether, expandable advanced transport and diagnostics. One fixed bottom Save all button targets the displayed selected slot and saves the complete form plus credentials and CA. No separate password-only, parameter-only, app-only or nonsecret preset buttons. Legacy credential storage remains behind one action. Old ten/four-slot backups remain importable; old files cannot recreate missing values. Complete WBPC file carries actual password/key/CA for every saved server; no device-local live Network handle. Global CN rule library is a shared resource, not per-server data. No upload or automatic export.

Old A12 standalone device selftest removed from production APK build and UI; historical sources remain for reference. Existing actual production diagnostic report, DNS/traffic/FEC status and network restore in lower menu. Keep optional advanced SIT settings hidden under advanced. No new runtime probes, data-path changes or protocol work.

CI requests signed Android API35/36 UI complete save/restore plus real SAF export/import, host complete codec roundtrip including >64KiB CA, native real seven modes/normal-managed/reconnect and BPF scenario. Physical phone UI and tether evidence still not claimed. UI test uses only disposable fixture credentials.

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Simplify daily APK UI, complete portable server profile save and backup, retire standalone debug asset."}
```
