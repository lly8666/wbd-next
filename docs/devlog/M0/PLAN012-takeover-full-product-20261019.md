# M0 intent and recovery — take over M1/M3 undelivered PLAN012 scopes

Exact main `58f7bc8abd631653c6ce7aacf7d728da40379f90`, no pending Actions on main, rev2 epoch1. M1 H29 Game015 prior module PASS, M3 H48 FEC018 ISA-L+wire native PASS; neither M1-016 nor M3-019 delivered real SOURCE despite registry task publication. User requested direct M0 solution instead of waiting. Original worker completion facts remain, M4 unaffected.

Atomic same commit decision + registry change: mark M1/M3 `integrated`, leave their task IDs and cursors as historical, M0 single active main product owner for `wbd-codec` release-record gate and new `v4_game_lane` adapter. No original M1/M3 code is rewritten unnecessarily. Before new actions, do not enable production FEC2; request from user is conditional after all qualification, not license for unverified default ON. One combined end-to-end Actions once all compile layers are ready. Exact SOURCE/observed outcomes to follow in S then H.
