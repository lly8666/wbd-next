"""Cheap Actions-only kernel command coverage; never a product/performance PASS."""
import os
import secrets
from .config import impairment, netem_args
from .runner import command


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() != 0:
        raise RuntimeError("Actions root-owned isolated namespace only")
    ns = "wbn-options-" + secrets.token_hex(4)
    command(["ip", "netns", "add", ns])
    try:
        prefix = ["ip", "netns", "exec", ns]
        command(prefix + ["ip", "link", "set", "lo", "up"])
        options = [{}, {"delay_ms": 25, "jitter_ms": 5, "loss_pct": 5, "duplicate_pct": 2, "reorder_pct": 5},
                   {"gemodel": [1, 20, 90, .1]}, {"delay_ms": 300, "rate_mbps": 8}]
        for i, raw in enumerate(options):
            args = netem_args(impairment(raw, 4), None, 32768)
            command(prefix + ["tc", "qdisc", "add" if i == 0 else "change", "dev", "lo", "root", "handle", "100:", "netem", *args])
            print(command(prefix + ["tc", "-s", "-j", "qdisc", "show", "dev", "lo"]))
        command(prefix + ["tc", "qdisc", "del", "dev", "lo", "root"])
        command(prefix + ["tc", "qdisc", "add", "dev", "lo", "root", "handle", "1:", "prio", "bands", "4", "priomap", *("0" for _ in range(16))])
        for lane in range(4):
            command(prefix + ["tc", "qdisc", "add", "dev", "lo", "parent", f"1:{lane+1}", "handle", f"{100+lane}:", "netem", "loss", "1%"])
            command(prefix + ["tc", "filter", "add", "dev", "lo", "parent", "1:", "protocol", "ip", "pref", str(10+lane),
                              "flower", "ip_proto", "tcp", "dst_port", str(443+lane), "classid", f"1:{lane+1}"])
        print(command(prefix + ["tc", "-s", "-j", "qdisc", "show", "dev", "lo"]))
        print("KERNEL_NETEM_OPTIONS_AND_FOUR_LANE_FILTERS_PASS_NOT_PRODUCT")
    finally:
        command(["ip", "netns", "del", ns], check=False)


if __name__ == "__main__":
    main()
