# 2026-11-16 — Manual network restore + synthetic Wi-Fi/USB forwarding workpack

- Branch: `experiment/android-temp-root-probe`; recorded HEAD before modification: `cf103182f1bc74d52ee3846272b542755ba4e6e6`. Existing KSU fully green ACTION `43843733837` is prior source and will not be relabelled as this new SOURCE PASS.
- User changes the recovery expectation: acceptable to have manual `一键恢复正常网络` after App reopens, instead of guaranteed instant recovery on crash. No automatic broad `ip rule flush`, iptables global cleanup or reboot/root installer.
- Code introduced `recover`/`recover-seed` native exact /32 legacy owned rule and ordinary target37 `RecoveryActivity` button; UI test must click real widget and verify `RESTORED` then `ALREADY_CLEAN` from App→KSU su UID0. Real hardware guarded off until durable owned journal exists.
- New `tethergate` uses Linux private empty namespace, synthetic Wi-Fi subnet `10.128.11.0/24` with TWO clients and USB subnet `10.128.12.0/24` with one, SNAT to `198.18.253.1` and injected peer TUN with conntrack reverse. No real Wi-Fi/USB, BPF offload, physical underlay or CLAT can be qualified.
- New same KSU AVD source-locked scene added after prior appflow, mainstream DNS/TLS and worker SIGKILL; single new Action will capture success or exact failures. No other workflow dispatched manually.
- Physical acceptance remains NOT_RUN. Do not promote feature card until same-SOURCE CI evidence is captured.

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Workpack for explicit App network recovery UI and isolated kernel SNAT multi-downstream fixture; not real tether."}
```
