# Android16 CN geosite quick action: stale window-focus witness fix (2026-11-17)

At source `a49bd16c6d6d8728597bf0ad21745b18784ab805`, [KSU run 43951593575](https://github.com/lly8666/wbd-next/actions/runs/43951593575) finished **FAIL**, while source-locked NDK/target37 APK build, real KSU App→su, TUN/raw/IPv6, normal DNS/TLS, synthetic hotspot/USB conntrack NAT, manual recovery and 10/10 UID kernel policy tests passed. The new complete CN geosite (8,503 rules) was packaged with SHA256 and license.

The App's `SplitSettingsActivity` wrote `wbd-split-ui-bounds.json` during `onCreate`, when `window_focused=false`, then did not update that flag upon Android WindowManager granting focus. The newly visible quick Root DNS button was at [24,248][296,308] but the CI gate read stale `window_focused=false` and exited **before any real click, App saved-config, Root geosite compilation or six DNS UDP/53 kernel round trips**. Do not classify this historical CI FAIL as a DNS feature failure or PASS.

Fix: refresh the same on-screen geometry+window focus witness from Android's genuine `onWindowFocusChanged` callback and again after `onResume` using the UI event queue, without synthesizing a click, writing config in CI, or modifying any Android netd route. The real one-tap App save→KSU native flow, immutable geosite SHA, DNS 6× real isolated kernel TUN egress/response evidence and untouched Android host policy remain mandatory. Actual physical hotspot, cellular, live DNS endpoints, WBD encrypted tunnel and DirtyFrag temporary Root remain **NOT_RUN**.

```feature-impact
{"kind":"none","ids":[],"reason":"Refresh Android SplitSettingsActivity real window-focus witness from lifecycle callbacks to unblock authentic visible quick DNS button test without fake click/config."}
```
