#!/usr/bin/env python3
"""Owned Linux kernel tc/IFB wiring for one real two-OS WL-N0 scenario.

Runs *inside the actual WSL2 Ubuntu guest*, never an application-level
impairment. Every changed kernel object is a unique owned object; foreign
qdiscs and interfaces are not overwritten. tc -s counters are evidence,
not proof of application latency without endpoint measurements.
"""
import json
import os
import pathlib
import subprocess
import sys
import time
from m0_wl_impairment_profile import get_profile

action, directory = sys.argv[1:3]
profile_name = sys.argv[3] if len(sys.argv)>3 else "n0"
scenario_path = sys.argv[4] if len(sys.argv)>4 else None
profile = get_profile(profile_name, side="windows", configfile=scenario_path)
egress_profile = get_profile(profile_name, side="linux", configfile=scenario_path)
out = pathlib.Path(directory)
out.mkdir(parents=True, exist_ok=True)
owner = out / "wl-n0-netem-owned.json"
iface = "ifbwlm0"

def call(*cmd, checked=True):
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=18)
    if checked and p.returncode:
        raise RuntimeError(f"{' '.join(cmd)} exit={p.returncode} {p.stderr[-350:]}")
    return {"rc": p.returncode, "stdout": p.stdout[-12000:], "stderr": p.stderr[-350:]}

def probe():
    return {
        "source": os.environ.get("GITHUB_SHA"),
        "eth0": json.loads(call("tc", "-s", "-j", "qdisc", "show", "dev", "eth0")["stdout"] or "[]"),
        "ifb": json.loads(call("tc", "-s", "-j", "qdisc", "show", "dev", iface, checked=False)["stdout"] or "[]"),
        "ingress_filters": call("tc", "-s", "filter", "show", "dev", "eth0", "ingress", checked=False)["stdout"],
        "utc": time.time(),
    }

def persist(state):
    owner.write_text(json.dumps(state, indent=2) + "\n")

def clean():
    if not owner.exists():
        print("WL_N0_KERNEL_NETEM_NO_OWNED_STATE", flush=True)
        return
    state = json.loads(owner.read_text())
    if state.get("owner") != "M0-WL-N0-ETH0-IFB" or state.get("interface") != iface:
        raise RuntimeError("refusing foreign netem state")
    errors = []
    # Delete only exact owned handle/ifb. Keep state if any cleanup failed.
    if state.get("ingress"):
        r = call("tc", "qdisc", "del", "dev", "eth0", "handle", "ffff:", "ingress", checked=False)
        if r["rc"]: errors.append("owned ingress removal: " + r["stderr"])
        else: state["ingress"] = False
    if state.get("egress"):
        r = call("tc", "qdisc", "del", "dev", "eth0", "root", checked=False)
        if r["rc"]: errors.append("owned egress removal: " + r["stderr"])
        else: state["egress"] = False
    if state.get("ifb_created"):
        r = call("ip", "link", "del", iface, checked=False)
        if r["rc"]: errors.append("owned ifb removal: " + r["stderr"])
        else: state["ifb_created"] = False
    persist(state)
    if errors: raise RuntimeError("; ".join(errors))
    owner.unlink()
    print("WL_N0_KERNEL_NETEM_ALL_OWNED_RESOURCES_REMOVED", flush=True)

if action == "arm":
    if owner.exists():
        raise RuntimeError("refusing preexisting netem ownership")
    # 'noqueue' or a simple default root is replaceable, but NEVER a foreign
    # configured netem/prio/tbf/HTB policy on the real test interface.
    existing = json.loads(call("tc", "-j", "qdisc", "show", "dev", "eth0")["stdout"])
    if any(x.get("kind") not in ("noqueue", "pfifo_fast", "fq_codel", "mq") and
           x.get("parent") in ("root", None) for x in existing):
        raise RuntimeError("foreign eth0 root qdisc; refuse overwrite: " + repr(existing))
    ingress = call("tc", "qdisc", "show", "dev", "eth0")["stdout"]
    if "ffff:" in ingress:
        raise RuntimeError("foreign eth0 ingress; refuse overwrite")
    # Existing IFB is not ours; no implicit rm.
    if call("ip", "link", "show", iface, checked=False)["rc"] == 0:
        raise RuntimeError("foreign ifb device name exists")
    state = {"owner": "M0-WL-N0-ETH0-IFB", "interface": iface,
             "profile": profile_name, "egress": False, "ingress": False, "ifb_created": False}
    persist(state)
    try:
        call("ip", "link", "add", iface, "type", "ifb")
        state["ifb_created"] = True; persist(state)
        call("ip", "link", "set", iface, "up")
        def native_netem(d):
            args=["netem","delay",f'{d["delay_ms"]}ms',
                  "loss",f'{d["loss_pct"]}%',"limit","32768"]
            if d["tc_mbit"] is not None:
                args += ["rate",f'{d["tc_mbit"]}mbit']
            return args
        call("tc", "qdisc", "add", "dev", iface, "root", "handle", "10:", *native_netem(profile))
        call("tc", "qdisc", "add", "dev", "eth0", "root", "handle", "20:", *native_netem(egress_profile))
        state["egress"] = True; persist(state)
        call("tc", "qdisc", "add", "dev", "eth0", "handle", "ffff:", "ingress")
        state["ingress"] = True; persist(state)
        # Only the original TCP-like Windows client → Linux public server
        # packets are mirrored. Other incoming WSL/host control traffic stays
        # outside the measured path. tc on IFB is the actual ingress delay.
        call("tc", "filter", "add", "dev", "eth0", "parent", "ffff:",
             "protocol", "ip", "prio", "1", "u32",
             "match", "ip", "protocol", "6", "0xff",
             "match", "ip", "dport", "443", "0xffff",
             "action", "mirred", "egress", "redirect", "dev", iface)
        snapshot = probe()
        root = [x for x in snapshot["eth0"] if x.get("kind") == "netem"]
        incoming = [x for x in snapshot["ifb"] if x.get("kind") == "netem"]
        if len(root) != 1 or len(incoming) != 1 or "mirred" not in snapshot["ingress_filters"]:
            raise RuntimeError("real tc netem root/IFB/ingress readback incomplete")
        snapshot["declared_profile"] = profile_name
        snapshot["requested_kernel_profile"] = profile
        snapshot["requested_linux_egress_profile"] = egress_profile
        (out / "wl-n0-netem-before.json").write_text(json.dumps(snapshot, indent=2) + "\n")
        marker=("WL_N0_GENUINE_KERNEL_300MS_BOTH_DIRECTIONS_CONFIGURED" if profile_name=="n0"
                else "WL_V2_GENUINE_KERNEL_BIDIRECTIONAL_SCENE_CONFIGURED" if profile_name=="v2"
                else "WL_P200_GENUINE_KERNEL_200MS_30PCT_250MBIT_BOTH_DIRECTIONS_CONFIGURED")
        print(marker,flush=True)
    except Exception:
        clean()
        raise
elif action == "snapshot":
    if not owner.exists(): raise RuntimeError("no owned netem state for readback")
    if json.loads(owner.read_text()).get("profile") != profile_name: raise RuntimeError("impairment profile mismatch")
    snapshot = probe()
    (out / "wl-n0-netem-after.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    print("WL_N0_GENUINE_KERNEL_TC_STATS_CAPTURED", flush=True)
elif action == "cleanup":
    clean()
else:
    raise SystemExit("expected arm/snapshot/cleanup")
