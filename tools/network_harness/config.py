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
    if "policy" in r and r["policy"] not in ["legacy-two-repair-v1", "outer-single-repair-v2"]:
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
    # Current public CLI hardcodes Game FEC off and exposes neither cipher nor repair knobs.
    if p.get("game_fec", "off") != "off" or any(k in p for k in ["cipher", "repair_enabled", "repair_ratio"]):
        raise Unsupported("current public CLI does not expose requested Game-FEC/cipher/repair setting")
    if p["mode"] == "fec-auto" and p["fec_profile"] != 1:
        raise Unsupported("auto startup is product-controlled; fec_profile cannot set it")
    lanes = {"game2": 2, "game4": 4}.get(p["mode"], 1)
    t = r["traffic"]
    keys(t, ["c2s_mbps", "s2c_mbps", "udp_share", "sizes", "tcp_flows", "probe_hz",
             "deadline_ms", "burst_ms", "max_packets", "allow_fragmentation"], "traffic")
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
    number(t["probe_hz"], 1, 100, "probe_hz")
    number(t["deadline_ms"], 1, 10000, "deadline_ms")
    number(t["burst_ms"], 0, 100, "burst_ms")
    integer(t["max_packets"], 1, 20000000, "max_packets")
    if type(t["allow_fragmentation"]) is not bool:
        raise ValueError("allow_fragmentation must be boolean")
    if not isinstance(t.get("sizes"), list) or not 1 <= len(t["sizes"]) <= 32:
        raise ValueError("sizes: 1..32 [application payload bytes, weight] pairs")
    for size, weight in t["sizes"]:
        integer(size, 64, 65507, "application payload size")
        integer(weight, 1, 100, "size weight")
    if sum(w for _, w in t["sizes"]) > 512:
        raise ValueError("size cycle too large")
    n = r.setdefault("network", {})
    keys(n, ["outer_mtu", "lane_loss", "queue_packets", "netem_rng"], "network")
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
    r.setdefault("warmup_s", 10)
    r.setdefault("drain_s", 5)
    number(r["warmup_s"], 1, 60, "warmup_s")
    number(r["drain_s"], 1, 30, "drain_s")
    if not isinstance(r.get("phases"), list) or not 1 <= len(r["phases"]) <= 16:
        raise ValueError("phases: 1..16 declared stages of ONE scenario")
    seen = set()
    for ph in r["phases"]:
        keys(ph, ["name", "seconds", "c2s", "s2c", "rate_scale"], "phase")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", ph.get("name", "")) or ph["name"] in seen:
            raise ValueError("invalid/duplicate phase name")
        seen.add(ph["name"])
        number(ph["seconds"], 0.05, 600, "phase seconds")
        ph.setdefault("rate_scale", 1)
        number(ph["rate_scale"], 0, 1, "rate_scale")
        for direction in ["c2s", "s2c"]:
            ph[direction] = impairment(ph.get(direction, {}), lanes)
    if sum(ph["seconds"] for ph in r["phases"]) > 1200:
        raise ValueError("one run maximum 1200 measured seconds")
    a = r.setdefault("acceptance", {})
    keys(a, ["injection_tolerance_pct", "max_loss_pct", "max_p99_ms",
             "max_active_gap_ms", "require_retransmission"], "acceptance")
    a.setdefault("injection_tolerance_pct", 3)
    a.setdefault("require_retransmission", False)
    number(a["injection_tolerance_pct"], 0.1, 10, "injection tolerance")
    for k, hi in [("max_loss_pct", 100), ("max_p99_ms", 30000), ("max_active_gap_ms", 30000)]:
        if k in a:
            number(a[k], 0, hi, k)
    if type(a["require_retransmission"]) is not bool:
        raise ValueError("require_retransmission must be boolean")
    bundles = r.get("bundles", {})
    if not isinstance(bundles, dict) or set(bundles) not in [{"A"}, {"A", "B"}]:
        raise ValueError("bundles must contain A, optionally B")
    for label, b in bundles.items():
        keys(b, ["source", "run_id", "attempt", "artifact_id", "sha256",
                 "step_attested_failure"], f"bundle {label}")
        if "step_attested_failure" in b and type(b["step_attested_failure"]) is not bool:
            raise ValueError("step_attested_failure must be boolean")
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
