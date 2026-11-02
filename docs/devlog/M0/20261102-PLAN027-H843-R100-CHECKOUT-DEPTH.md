# PLAN027 H843 | Bounded git depth for original f5 high-PPS R pairing

- H842 [Action 41365296589](https://github.com/lly8666/wbd-next/actions/runs/41365296589) failed at **pre-native** `git cat-file -e "$PRODUCT_SOURCE^{commit}"` because default checkout fetched only HEAD and SOURCE f5 was an older ancestor. No binaries downloaded, no UDP/CPU measured. This is **FIXTURE FAIL**, not 100Mbps product or repair ON FAIL.
- Only change same existing Action's checkout to `fetch-depth:80`, enough to resolve source f5; exact same frozen SHA-manifest original client/server/lib, same 100Mbps/25ms/0%/1200B same-VM ordered OFF→ON scenario and thresholds, no new product or CPU tuning.
- H841 new Go original cold reauth fdc source build PASS, actual 105s blackhole restoration job in progress, unrelated independent native run.
```feature-impact
{"kind":"none","ids":[],"reason":"Fix preflight git ancestry checkout depth for source-frozen sameVM R cost test, no product/default change."}
```
