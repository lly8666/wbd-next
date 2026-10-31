# PLAN027 H605 — original Game push path trigger and feature card

Recovered H604 SOURCE `a3fb3464965eab45e489d10fd0ac657d6d2b7984`: no real Windows/WSL2 native Action was triggered, because the two real Go Game product source paths were missing from the signed native workflow's push filter. H604 governance [41188990553](https://github.com/lly8666/wbd-next/actions/runs/41188990553) failed only Feature catalog: `declared feature card not updated: windows-native-transport`. Neither failure proves business failure or success.

Add just the two Go Game native sources to the existing signed Windows/WSL2 workflow's exact push paths, keep the current Game watchdog tiers/manifest unchanged, and scope the new commit to **one Game2** via the existing `[plan026-game2-only]` marker. Update the existing feature card to record H604 abort reader lifetime fix and absence of fresh native qualification, without promoting old results. Previous H601 Game2 run41186157073 CANCELLED without product Stop; H604/H605 Game2/4 FEC, lifecycle/rotation and PLAN027 A/B/C/long still require evidence.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Reflect bounded Game reader abort cleanup and restore same-SOURCE CI trigger for both product source paths; no new business/protocol behavior in H605."}
```
