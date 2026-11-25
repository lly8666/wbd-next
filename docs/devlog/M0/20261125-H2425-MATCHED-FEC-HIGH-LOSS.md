# H2425 matched FEC and high loss

H2425 freezes H2423 product SOURCE and exact artifact 14995813926. Five independent scenarios, each ABBA and BAAB: NAT fq600 vs NAT fq disabled both endpoints (same runner mechanism); 5%/400ms NAT BBR vs splice BBR both fixed mild profile1; 10%/400ms splice BBR mild25% vs balanced50% (profile3); 15%/400ms NAT BBR vs splice BBR both balanced; 30%/400ms NAT BBR vs splice BBR both maximum125% profile6. No FEC OFF cross-condition attribution. Fixed profiles intentionally chosen as diagnostic, not default recommendation or sweep for optimal parameters. 30% may be incomplete: retain raw failure; do not promote. Actual FEC per-client readback and recovered TUN counts, host/socket/queue receipts, fresh one-shot origins, pre/post capacity. No product modifications, no new CC, no physical WAN/three-runner qualification. H2424 results in docs/evidence/M0/20261125-H2424-MECHANISMS.json.

```feature-impact
{"kind":"none","ids":[],"reason":"Frozen product diagnostic harness and evidence only."}
```
