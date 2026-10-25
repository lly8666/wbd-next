"""Small strict request format. Unsupported product knobs must not be ignored."""
import copy
import math
import re


class Unsupported(ValueError):
    pass


def keys(value, allowed, where):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"{where}: unknown fields or not an object")


def number(v, lo, hi, where):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f"{where}: expected finite {lo}..{hi}")
    return v


def integer(v, lo, hi, where):
    number(v, lo, hi, where)
    if not isinstance(v, int):
        raise ValueError(f"{where}: integer required")
    return v


def impairment(raw, lanes):
    keys(raw, ["delay_ms", "jitter_ms", "loss_pct", "duplicate_pct", "reorder_pct",
               "rate_mbps", "blackhole_lanes", "gemodel"], "impairment")
    d = {"delay_ms": 0, "jitter_ms": 0, "loss_pct": 0, "duplicate_pct": 0,
         "reorder_pct": 0, "rate_mbps": 0, "blackhole_lanes": []}
    d.update(raw)
    for k in ["delay_ms", "jitter_ms"]:
        number(d[k], 0, 2000, k)
    for k in ["loss_pct", "duplicate_pct", "reorder_pct"]:
        number(d[k], 0, 100, k)
    number(d["rate_mbps"], 0, 10000, "rate_mbps")
    if d["jitter_ms"] > d["delay_ms"] or (d["reorder_pct"] and not d["delay_ms"]):
        raise ValueError("jitter requires sufficient delay; reorder requires nonzero delay")
    if not isinstance(d["blackhole_lanes"], list):
        raise ValueError("blackhole_lanes must be a list")
    for n in d["blackhole_lanes"]:
        integer(n, 1, lanes, "blackhole lane")
    if len(set(d["blackhole_lanes"])) != len(d["blackhole_lanes"]):
        raise ValueError("duplicate blackhole lane")
    if "gemodel" in d:
        if d["loss_pct"]:
            raise ValueError("random loss and gemodel are mutually exclusive")
        if not isinstance(d["gemodel"], list) or len(d["gemodel"]) != 4:
            raise ValueError("gemodel=[P,R,1-H,1-K], all in percent")
        for v in d["gemodel"]:
            number(v, 0, 100, "gemodel")
    return d


def validate(raw):
    r = copy.deepcopy(raw)
    keys(r, ["version", "id", "owner", "seed", "policy", "product", "traffic", "network",
             "warmup_s", "drain_s", "phases", "acceptance", "bundles", "order"], "request")
    if "policy" in r and r["policy"] not in ["legacy-two-repair-v1", "outer-single-repair-v2", "outer-opportunistic-v3"]:
        raise ValueError("unknown recovery policy")
    if r.get("version") != 1:
        raise ValueError("version must be 1")
    for k in ["id", "owner"]:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", r.get(k, "")):
            raise ValueError(f"invalid {k}")
    integer(r.get("seed"), 1, 2147483000, "seed")
    p = r["product"]
    keys(p, ["mode", "fec_profile", "game_fec", "cipher", "repair_enabled", "repair_ratio"], "product")
    if p.get("mode") not in ["normal", "fec-fixed", "fec-auto", "game2", "game4"]:
        raise Unsupported("public V4 adapter has no such mode")
    p.setdefault("fec_profile", 1)
    integer(p["fec_profile"], 0, 6, "fec_profile")
    # Two-sided native OFF is an actual product policy, never analyzer-only.
    if "repair_enabled" in p and type(p["repair_enabled"]) is not bool:
        raise ValueError("repair_enabled must be boolean")
    if p.get("game_fec", "off") != "off" or any(k in p for k in ["cipher", "repair_ratio"]):
        raise Unsupported("current public CLI does not expose requested Game-FEC/cipher setting")
    if p.get("repair_enabled") is False and p["mode"] in ("game2", "game4"):
        raise Unsupported("outer repair off not wired to public Game")
    if p["mode"] == "fec-auto" and p["fec_profile"] != 1:
        raise Unsupported("auto startup is product-controlled; fec_profile cannot set it")
    lanes = {"game2": 2, "game4": 4}.get(p["mode"], 1)
    t = r["traffic"]
    keys(t, ["c2s_mbps", "s2c_mbps", "udp_share", "sizes", "tcp_flows", "probe_hz",
             "deadline_ms", "burst_ms", "max_packets", "allow_fragmentation",
             "observe_independent_flows", "observe_size_classes"], "traffic")
    for k in ["c2s_mbps", "s2c_mbps"]:
        number(t.get(k), 0, 500, k)
    if not t["c2s_mbps"] and not t["s2c_mbps"]:
        raise ValueError("one direction must offer traffic")
    for k, v in {"udp_share": 1, "tcp_flows": 2, "probe_hz": 10,
                 "deadline_ms": 250, "burst_ms": 0, "max_packets": 10000000,
                 "allow_fragmentation": False}.items():
        t.setdefault(k, v)
    number(t["udp_share"], 0, 1, "udp_share")
    integer(t["tcp_flows"], 1, 16, "tcp_flows")
    number(t["probe_hz"], 0, 100, "probe_hz")
    number(t["deadline_ms"], 1, 10000, "deadline_ms")
    number(t["burst_ms"], 0, 100, "burst_ms")
    integer(t["max_packets"], 1, 20000000, "max_packets")
    if type(t["allow_fragmentation"]) is not bool:
        raise ValueError("allow_fragmentation must be boolean")
    t.setdefault("observe_independent_flows",False)
    if type(t["observe_independent_flows"]) is not bool:
        raise ValueError("observe_independent_flows must be boolean")
    t.setdefault("observe_size_classes",False)
    if type(t["observe_size_classes"]) is not bool:
        raise ValueError("observe_size_classes must be boolean")
    if t["observe_size_classes"] and not (r.get("owner")=="fec-network-work" and t["udp_share"]>0):
        raise ValueError("size classes are scoped to FEC owned real UDP")
    if not isinstance(t.get("sizes"), list) or not 1 <= len(t["sizes"]) <= 32:
        raise ValueError("sizes: 1..32 [application payload bytes, weight] pairs")
    for size, weight in t["sizes"]:
        integer(size, 64, 65507, "application payload size")
        integer(weight, 1, 100, "size weight")
    if sum(w for _, w in t["sizes"]) > 512:
        raise ValueError("size cycle too large")
    n = r.setdefault("network", {})
    keys(n, ["outer_mtu", "lane_loss", "queue_packets", "netem_rng",
             "tcp_window_profiles", "tcp_reordering_profiles", "v3_timeline",
             "tun_txqlen_profiles", "warmup_rate_scale_profiles", "tun_qdisc_profiles",
              "startup_tun_drop_timeline", "fec_egress_diagnostic", "tcp_socket_pacing_mbps_profiles",
              "tun_fq_maxrate_mbps_profiles", "product_tun_fq_maxrate_mbps_profiles",
              "owned_veth_static_neighbour"], "network")
    # Test-owned veth peer L2 is directly attached with a stable MAC.
    # Pinning ONLY this neighbour avoids impairing ARP discovery when netem
    # applies real 30% loss to every frame including control-plane ARP.
    # Public product and all host routes/ARP remain untouched.
    n.setdefault("owned_veth_static_neighbour",False)
    if type(n["owned_veth_static_neighbour"]) is not bool:
        raise ValueError("network.owned_veth_static_neighbour must be boolean")
    n.setdefault("fec_egress_diagnostic",False)
    if type(n["fec_egress_diagnostic"]) is not bool:
        raise ValueError("network.fec_egress_diagnostic must be boolean")
    n.setdefault("v3_timeline", False)
    if type(n["v3_timeline"]) is not bool:
        raise ValueError("network.v3_timeline must be boolean")
    n.setdefault("startup_tun_drop_timeline",False)
    if type(n["startup_tun_drop_timeline"]) is not bool:
        raise ValueError("network.startup_tun_drop_timeline must be boolean")
    n.setdefault("outer_mtu", 1500)
    n.setdefault("lane_loss", "shared")
    n.setdefault("queue_packets", 32768)
    n.setdefault("netem_rng", "unseeded_recorded")
    if n["netem_rng"] not in ["seeded", "unseeded_recorded"]:
        raise ValueError("netem_rng must be seeded or unseeded_recorded")
    integer(n["outer_mtu"], 1280, 9000, "outer_mtu")
    integer(n["queue_packets"], 1024, 131072, "queue_packets")
    if n["lane_loss"] not in ["shared", "independent"]:
        raise ValueError("lane_loss must be shared or independent")
    profiles=n.setdefault("tcp_window_profiles",{})
    keys(profiles,["A","B"],"tcp_window_profiles")
    if not all(v in ("baseline","large","bdp500") for v in profiles.values()):
        raise ValueError("tcp_window_profiles must be baseline or large")
    pacing=n.setdefault("tcp_socket_pacing_mbps_profiles",{})
    keys(pacing,["A","B"],"tcp_socket_pacing_mbps_profiles")
    # Test-only per-socket SO_MAX_PACING_RATE. No host/netns sysctl writes,
    # no change to real WBD kernel/TUN configuration or offered app target.
    for leg,v in pacing.items():
        if type(v) is not int or v not in (0,600):
            raise ValueError("test-only TCP socket pacing must be 0 or 600Mbps")
    qlens=n.setdefault("tun_txqlen_profiles",{})
    keys(qlens,["A","B"],"tun_txqlen_profiles")
    # STRICT TEST-ONLY options to distinguish a short kernel TUN burst
    # against its default500 ring. 1024 ~23ms and 2048 ~47ms of near-MTU
    # at 500Mbps; never change product default or use unbounded sizes.
    for leg,qlen in qlens.items():
        integer(qlen,500,2048,"tun_txqlen_profiles."+leg)
        if qlen not in (500,1024,2048):
            raise ValueError("diagnostic TUN queue must be 500, 1024 or 2048")
    qdiscs=n.setdefault("tun_qdisc_profiles",{})
    keys(qdiscs,["A","B"],"tun_qdisc_profiles")
    if any(value not in ("fq_codel","fq") for value in qdiscs.values()):
        raise ValueError("tun_qdisc_profiles only fq_codel and fq for owned namespace")
    fq_maxrate=n.setdefault("tun_fq_maxrate_mbps_profiles",{})
    keys(fq_maxrate,["A","B"],"tun_fq_maxrate_mbps_profiles")
    for leg,rate in fq_maxrate.items():
        if type(rate) is not int or rate not in (0,600):
            raise ValueError("test-only TUN fq maxrate must be 0 or 600Mbps")
        if qdiscs.get(leg)!="fq":
            raise ValueError("TUN fq maxrate requires explicitly selected fq qdisc")
    owned_fq=n.setdefault("product_tun_fq_maxrate_mbps_profiles",{})
    keys(owned_fq,["A","B"],"product_tun_fq_maxrate_mbps_profiles")
    for leg,rate in owned_fq.items():
        if type(rate) is not int or rate not in (0,600):
            raise ValueError("owned Linux product TUN fq maxrate must be 0 or 600Mbps")
    # Every supported Linux product mode defaults owned TUN to fq600;
    # unset means OMIT CLI flag, not implicit disabling. Diagnostic tc
    # may touch that qdisc only when explicit0 was sent on the same leg.
    for leg in ("A","B"):
        effective=owned_fq.get(leg,600)
        if effective and (qdiscs.get(leg) is not None or fq_maxrate.get(leg)):
            raise ValueError("product TUN fq cannot be overridden by diagnostic qdisc in same leg")
    warm_scales=n.setdefault("warmup_rate_scale_profiles",{})
    keys(warm_scales,["A","B"],"warmup_rate_scale_profiles")
    for leg,scale in warm_scales.items():
        number(scale,0.05,1,"warmup_rate_scale_profiles."+leg)
    reorder=n.setdefault("tcp_reordering_profiles",{})
    keys(reorder,["A","B"],"tcp_reordering_profiles")
    if not all(v in ("baseline","outer_repair_tolerant") for v in reorder.values()):
        raise ValueError("tcp_reordering_profiles must be baseline or outer_repair_tolerant")
    r.setdefault("warmup_s", 10)
    r.setdefault("drain_s", 5)
    number(r["warmup_s"], 1, 60, "warmup_s")
    number(r["drain_s"], 1, 30, "drain_s")
    if not isinstance(r.get("phases"), list) or not 1 <= len(r["phases"]) <= 16:
        raise ValueError("phases: 1..16 declared stages of ONE scenario")
    seen = set()
    for ph in r["phases"]:
        keys(ph, ["name", "seconds", "c2s", "s2c", "rate_scale", "product_cpu_stress"], "phase")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", ph.get("name", "")) or ph["name"] in seen:
            raise ValueError("invalid/duplicate phase name")
        seen.add(ph["name"])
        number(ph["seconds"], 0.05, 600, "phase seconds")
        ph.setdefault("rate_scale", 1)
        number(ph["rate_scale"], 0, 1, "rate_scale")
        # FEC-owned 0%-netem test-only product CPU contention. Never affects
        # other jobs, a production knob, a traffic injector or the host globally.
        stress=ph.get("product_cpu_stress")
        if stress is not None:
            if r.get("owner")!="fec-network-work" or p["mode"]!="fec-auto" or p.get("repair_enabled") is not False:
                raise Unsupported("product CPU stress is FEC-only Auto with real outer repair off")
            keys(stress, ["role","competitors"], "product_cpu_stress")
            if stress.get("role") not in ("client","server"):
                raise ValueError("product_cpu_stress.role must be client or server")
            integer(stress.get("competitors"), 1, 48, "product_cpu_stress.competitors")
        for direction in ["c2s", "s2c"]:
            ph[direction] = impairment(ph.get(direction, {}), lanes)
            if stress is not None and (ph[direction]["loss_pct"]!=0 or
                ph[direction]["duplicate_pct"]!=0 or ph[direction]["reorder_pct"]!=0 or
                ph[direction]["blackhole_lanes"]):
                raise ValueError("CPU stress experiment must keep both network lanes loss/reorder/blackhole free")
    if sum(ph["seconds"] for ph in r["phases"]) > 1200:
        raise ValueError("one run maximum 1200 measured seconds")
    a = r.setdefault("acceptance", {})
    keys(a, ["injection_tolerance_pct", "max_loss_pct", "max_p99_ms",
             "max_active_gap_ms", "require_retransmission", "max_repair_fresh_pct", "min_repair_line_pct",
             "require_zero_source_tun_drops_full_run",
              "require_zero_tun_root_qdisc_drops_full_run", "cross_business_hol",
             "max_small_udp_loss_pct", "max_small_udp_p99_ms", "loss_gate_phases",
             "require_native_m2_positive_confirmation"], "acceptance")
    a.setdefault("injection_tolerance_pct", 3)
    a.setdefault("require_retransmission", False)
    a.setdefault("require_zero_source_tun_drops_full_run", False)
    a.setdefault("require_zero_tun_root_qdisc_drops_full_run",False)
    a.setdefault("cross_business_hol",False)
    a.setdefault("require_native_m2_positive_confirmation",False)
    if type(a["require_native_m2_positive_confirmation"]) is not bool:
        raise ValueError("native positive M2 readback gate must be boolean")
    if a["require_native_m2_positive_confirmation"] and (
            r.get("owner")!="fec-network-work" or
            p["mode"] not in ("fec-fixed","fec-auto")):
        raise ValueError("native positive M2 receipt gate only for actual owned Fixed/Auto")
    if "loss_gate_phases" in a:
        gate=a["loss_gate_phases"]
        names={p["name"] for p in r["phases"]}
        if (r.get("owner")!="fec-network-work" or not isinstance(gate,list)
            or not gate or any(not isinstance(p,str) for p in gate)
            or len(set(gate))!=len(gate) or not set(gate)<=names):
            raise ValueError("loss_gate_phases must name distinct FEC-owned phases")
        if not all(k in a for k in ("max_loss_pct","max_small_udp_loss_pct")):
            raise ValueError("phase-scoped loss requires real total and small UDP gates")
    if any(k in a for k in ("max_small_udp_loss_pct","max_small_udp_p99_ms")) and not t["observe_size_classes"]:
        raise ValueError("small-packet gates require actual small-packet observations")
    if type(a["cross_business_hol"]) is not bool:
        raise ValueError("cross_business_hol must be boolean")
    if a["cross_business_hol"] and not (0 < t["udp_share"] < 1
            and t["tcp_flows"]>=2 and t["observe_independent_flows"]):
        raise ValueError("cross_business_hol requires UDP + two independent TCP streams + per-flow 10ms receipts")
    if type(a["require_zero_tun_root_qdisc_drops_full_run"]) is not bool:
        raise ValueError("require_zero_tun_root_qdisc_drops_full_run must be boolean")
    if type(a["require_zero_source_tun_drops_full_run"]) is not bool:
        raise ValueError("require_zero_source_tun_drops_full_run must be boolean")
    number(a["injection_tolerance_pct"], 0.1, 10, "injection tolerance")
    for k, hi in [("max_small_udp_loss_pct",100), ("max_small_udp_p99_ms",30000),
                  ("max_loss_pct", 100), ("max_p99_ms", 30000), ("max_active_gap_ms", 30000),
                  ("max_repair_fresh_pct", 100), ("min_repair_line_pct", 100)]:
        if k in a:
            number(a[k], 0, hi, k)
    if type(a["require_retransmission"]) is not bool:
        raise ValueError("require_retransmission must be boolean")
    bundles = r.get("bundles", {})
    if not isinstance(bundles, dict) or set(bundles) not in [{"A"}, {"A", "B"}]:
        raise ValueError("bundles must contain A, optionally B")
    for label, b in bundles.items():
        keys(b, ["source", "run_id", "attempt", "artifact_id", "sha256",
                 "step_attested_failure", "recovery_policy", "diagnostic_10x", "repair_enabled"], f"bundle {label}")
        if "step_attested_failure" in b and type(b["step_attested_failure"]) is not bool:
            raise ValueError("step_attested_failure must be boolean")
        if "diagnostic_10x" in b and type(b["diagnostic_10x"]) is not bool:
            raise ValueError("diagnostic_10x must be boolean")
        if "repair_enabled" in b and type(b["repair_enabled"]) is not bool:
            raise ValueError("bundle repair_enabled must be boolean")
        if b.get("repair_enabled") is False and p["mode"] in ("game2", "game4"):
            raise Unsupported("outer repair off not wired to public Game")
        if "recovery_policy" in b and b["recovery_policy"] not in ("legacy-two-repair-v1", "outer-single-repair-v2", "outer-opportunistic-v3"):
            raise ValueError("invalid per-bundle recovery policy")
        for k, length in [("source", 40), ("sha256", 64)]:
            if not re.fullmatch("[0-9a-f]{%d}" % length, b.get(k, "")):
                raise ValueError(f"bundle {k} must be exact full hex")
        for k in ["run_id", "attempt", "artifact_id"]:
            integer(b.get(k), 1, 10**15, k)
    r.setdefault("order", "A" if len(bundles) == 1 else "AB")
    if r["order"] not in (["A"] if len(bundles) == 1 else ["AB", "BA"]):
        raise ValueError("order must be A or predeclared AB/BA; no overlapping measurements")
    return r


def netem_args(d, seed, limit):
    args = ["limit", str(limit)]
    if d["delay_ms"]:
        args += ["delay", f'{d["delay_ms"]}ms']
        if d["jitter_ms"]:
            args += [f'{d["jitter_ms"]}ms']
    if "gemodel" in d:
        args += ["loss", "gemodel"] + [f"{v}%" for v in d["gemodel"]]
    elif d["loss_pct"]:
        args += ["loss", "random", f'{d["loss_pct"]}%']
    for field, option in [("duplicate_pct", "duplicate"), ("reorder_pct", "reorder")]:
        if d[field]:
            args += [option, f'{d[field]}%']
    if d["rate_mbps"]:
        args += ["rate", f'{d["rate_mbps"]}mbit']
    if seed is not None:
        args += ["seed", str(seed)]
    return args


def fec_residual(k, r, p):
    """Ideal IID systematic RS: tagged source lost AND >=r of other symbols lost."""
    n = k + r - 1
    return p * sum(math.comb(n, j) * p**j * (1-p)**(n-j) for j in range(r, n+1))
