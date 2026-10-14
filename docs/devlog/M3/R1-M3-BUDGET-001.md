# R1-M3-BUDGET-001

S: Rust single-owner path_budget module and independent literal old-Go pathmtu budget oracle. Pinned Go SOURCE lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984 internal/pathmtu/{budget.go,budget_test.go}; no Go changes.

IP/TCP actual serialized headers, peer SYN MSS or 536 fallback, optional local ceiling, protected-admission record cap, record fixed 31B, optional FEC reservation 56B, LINK20 only for fragmented packets; Game16 once before LINK. Fixed off normal packet is unwrapped; adaptive current off reserves FEC but sends plain LINK. Exposes link_frame_mtu to existing fragment_compat without subtracting again, record_wire_mtu to sealer; TUN ceiling uses nominal MSS not one peer and floors at IPv4 576. Startup padding uses remaining record payload.

R1 tests assert old-Go 6-MTU 0/4/20 parity matrix, options/MSS/local/record cap, nominal TUN floor, invalid and off minus/equal/plus edges against actual R0 fragment_compat wire. Source commit is unverified until native worker Actions; NOT AEAD, NOT product V4. No change to root Cargo/lock, shared ABI/types, CI or config/GUI (no new setting, this is internal ledger only). Next independent atom: real record AEAD Seal/Open + 8-byte HP, coordinate new Rust dependency/lock changes with M0.
