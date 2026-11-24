# H2335 — discard unproven hot-path increments; isolate synchronous OFF loan

H2327 (45310787767) all 9 jobs PASS but A/B/A′ g-a 206.258/166.317/163.362 Mbps and g-b 167.361/154.146/86.072; B vs mean -10.0%/+21.6%. CPU/GiB 28.1929/35.9281/36.4121 and 37.7147/36.3995/40.4452. H2326 not retained as a standalone product gain. H2331 (45311438312) all 9 jobs PASS but g-a 197.394/112.456/127.022 and g-b 149.938/122.992/116.335; -30.7%/-7.6%, CPU/GiB 27.5894/49.7567/41.6031 and 39.2529/44.4213/52.3103. H2330 not retained. All legs 160 echo, no late >1s, zero short NPF. Do not rewrite historical results. H2332 45311680513 PASS (26 owner + two 67 platform suites), maximum 45311680368 PASS; real gain unknown.

Restore native platform to measured H2323 (6fa10d7) exactly, and reconstruct only H2332 synchronous Normal/off original M1 loan on that source. Preserve H2318/H2320. Prior H2326 and H2330 removed from active production candidate, not erased from history. Native test on this reconstructed exact source and separate real AB required. Retain feature-impact/no promotion.

```feature-impact
{"kind":"none","ids":[],"reason":"Restore prior native path and isolate original synchronous Normal/off loan optimization; no protocol or feature promotion."}
```
