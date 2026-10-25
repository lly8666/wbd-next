"""Conservative result classification. Observation is never product qualification."""
import json
import math
from pathlib import Path
from .config import fec_residual


def snmp_counters(text):
    rows = text.splitlines()
    counters = {}
    for names, values in zip(rows[::2], rows[1::2]):
        a, b = names.split(), values.split()
        if a and b and a[0] == b[0]:
            counters.update({a[0].rstrip(":") + "." + k: int(v) for k, v in zip(a[1:], b[1:])})
    return counters


def network_accounting(snapshots):
    """Leaf netem only (do not double-count prio parents); all traffic, not DATA-only."""
    out = []
    stages = [s for s in snapshots if s["name"].startswith("before-") or s["name"] == "measurement-end"]
    for before, after in zip(stages, stages[1:]):
        for role in ["client", "server"]:
            a, b = before["network"][role], after["network"][role]
            qa = {q["handle"]: q for q in a["qdisc"] if q["kind"] == "netem"}
            qb = {q["handle"]: q for q in b["qdisc"] if q["kind"] == "netem"}
            leaf = []
            for handle, end in qb.items():
                start = qa.get(handle, {})
                packets = end.get("packets", 0) - start.get("packets", 0)
                dropped = end.get("drops", 0) - start.get("drops", 0)
                leaf.append({"handle": handle, "forwarded_packets": packets, "drops": dropped,
                             "counter_reset": packets < 0 or dropped < 0,
                             "approx_loss_pct": 100*dropped/(packets+dropped) if packets+dropped > 0 and dropped >= 0 else None,
                             "end_backlog_bytes": end.get("backlog"), "end_qlen": end.get("qlen")})
            sa, sb = snmp_counters(a["snmp"]), snmp_counters(b["snmp"])
            fields = ["Udp.RcvbufErrors", "Udp.SndbufErrors", "Udp.InErrors", "Ip.ReasmFails", "Ip.FragFails", "Tcp.RetransSegs"]
            out.append({"phase": before["name"][7:], "role": role, "netem": leaf,
                        "kernel_delta": {k: sb[k]-sa[k] for k in fields if k in sb and k in sa},
                        "interpretation": "all outer traffic incl ACK/control/repair; duplicates/backlog/queue overflow can bias netem ratio; inner TCP retrans separate"})
    return out


def active_gap(tx, rx, allowance_bins=0):
    """Only bins with ongoing offered business count; sparse silence is not HOL.

    Delay is separately reported; this metric is NOT a proof of protocol HOL.
    Sustained TX windows are compared with delayed RX bins, never compress time.
    """
    longest = run = 0
    for i, offered in enumerate(tx):
        j = i + allowance_bins
        if offered and j < len(rx) and not rx[j]:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest * 10


def cross_business_hol(config, client, server):
    """10ms true per-business delivery continuity in steady interior.

    Never label a TCP flow's *own* retransmission HOL a tunnel cross-HOL.
    Skip 2s after an impairment boundary and 1s before the next boundary:
    delayed packets/RTT across phases are not misleadingly bin-attributed.
    Inspect every UDP delivery and both independent TCP socket streams. Raw
    send/receive bins remain in the artifacts, not survivor-only histograms.
    """
    phases = [{"name":"warmup","seconds":config["warmup_s"]}] + config["phases"]
    out, failures, limits = {}, [], []
    elapsed = 0
    for ph in phases:
        first = round(elapsed*100)
        elapsed += ph["seconds"]
        last = round(elapsed*100)
        if ph["name"]=="warmup":
            continue
        lo, hi = first+200, last-100
        if hi<=lo:
            limits.append("HOL_"+ph["name"]+": steady interior insufficient for 2s/1s guard")
            continue
        for direction,tx,rx in (("c2s",client,server),("s2c",server,client)):
            tag=direction+"/"+ph["name"]
            src=tx["tx_bins_10ms"]["udp"]
            dst=rx["rx_bins_10ms"]["udp"]
            sent_tcp=tx.get("tcp_flow_tx_bins_10ms")
            received_tcp=rx.get("tcp_flow_rx_bins_10ms")
            n=config["traffic"]["tcp_flows"]
            if (sent_tcp is None or received_tcp is None or
                len(sent_tcp)!=n or len(received_tcp)!=n or
                min(len(src),len(dst),*[len(v) for v in sent_tcp+received_tcp])<hi):
                failures.append(tag+": missing independent 10ms TCP/UDP evidence")
                continue
            max_src_off = no_udp = no_all = 0
            src_run = udp_run = all_run = 0
            offered_bins = delivered_bins = shared_bins = 0
            for i in range(lo,hi):
                offered=src[i]>0
                got_udp=dst[i]>0
                got_tcp=any(flow[i]>0 for flow in received_tcp)
                src_run = 0 if offered else src_run+1
                max_src_off=max(max_src_off,src_run)
                udp_run = udp_run+1 if offered and not got_udp else 0
                no_udp=max(no_udp,udp_run)
                all_run = all_run+1 if offered and not got_udp and not got_tcp else 0
                no_all=max(no_all,all_run)
                offered_bins+=int(offered)
                delivered_bins+=int(got_udp)
                shared_bins+=int(got_udp or got_tcp)
            tcp_flows=[]
            for idx in range(n):
                tx_bins=sent_tcp[idx]
                rx_bins=received_tcp[idx]
                max_gap=gap=0
                delivered=0
                offered=0
                udp_forward_while_tcp_empty=0
                for i in range(lo,hi):
                    offered+=tx_bins[i]
                    delivered+=rx_bins[i]
                    gap=gap+1 if rx_bins[i]==0 else 0
                    max_gap=max(max_gap,gap)
                    udp_forward_while_tcp_empty+=int(rx_bins[i]==0 and dst[i]>0)
                tcp_flows.append({"id":idx,
                    "offered_packets_in_window":offered,
                    "delivered_packets_in_window":delivered,
                    "max_zero_delivery_ms":max_gap*10,
                    "udp_progress_bins_while_this_tcp_idle":udp_forward_while_tcp_empty})
                if offered>0 and delivered==0:
                    failures.append(tag+f": TCP independent flow {idx} never delivered")
            out[tag]={"scope":"OWNED_NAMESPACE_REAL_TCP_SOCKET_IDS_NOT_AGGREGATE",
                "phase_interior_guard_s":[2,1],
                "examined_10ms_bins":hi-lo,
                "udp_tx_active_bins":offered_bins,
                "udp_rx_active_bins":delivered_bins,
                "any_business_rx_active_bins":shared_bins,
                "longest_udp_sender_silence_ms":max_src_off*10,
                "longest_udp_receiver_zero_while_offered_ms":no_udp*10,
                "longest_ALL_business_receiver_zero_while_udp_offered_ms":no_all*10,
                "tcp_independent_socket_flows":tcp_flows}
            if max_src_off*10>100 or offered_bins<(hi-lo)*0.95:
                limits.append(tag+": offered UDP sender not continuously paced, HOL unqualified")
            if no_udp*10>100:
                failures.append(tag+": protected UDP blocked >100ms despite offered packets")
            if no_all*10>100:
                failures.append(tag+": all independent businesses blocked >100ms despite UDP offer")
    return out, failures, limits


def summarize(config, client, server, telemetry, host):
    failures, limits, observed, warnings = [], [], [], []
    phases = [{"name": "warmup", "seconds": config["warmup_s"], "rate_scale": 1}] + config["phases"]
    a = config["acceptance"]
    for direction, sender, receiver, rate in [("c2s", client, server, config["traffic"]["c2s_mbps"]),
                                               ("s2c", server, client, config["traffic"]["s2c_mbps"])]:
        for proto, share in [("udp", config["traffic"]["udp_share"]), ("tcp", 1-config["traffic"]["udp_share"])]:
            if not share:
                continue
            for i, ph in enumerate(phases):
                if not i:
                    continue
                tx, rx = sender["stats"][proto][i], receiver["stats"][proto][i]
                target = rate * share * ph["rate_scale"]
                injected = tx["tx_bytes"] * 8 / ph["seconds"] / 1e6
                # Cohort goodput counts late arrivals through drain. Do not call it in-phase wire rate.
                delivered = rx["rx_bytes"] * 8 / ph["seconds"] / 1e6
                missing = tx["tx_packets"] - rx["rx_packets"]
                loss = 100 * missing / tx["tx_packets"] if tx["tx_packets"] else None
                deadline_bad = missing + rx["late"]
                first_bin = round(sum(p["seconds"] for p in phases[:i]) * 100)
                last_bin = first_bin + round(ph["seconds"] * 100)
                arrival_bytes = receiver.get("rx_bytes_bins_10ms", {}).get(proto)
                row = {"direction": direction, "protocol": proto, "phase": ph["name"],
                       "target_app_mbps": target, "injected_app_mbps": injected,
                       "cohort_delivered_app_mbps": delivered, "sent": tx["tx_packets"],
                       "arrival_window_app_mbps": sum(arrival_bytes[first_bin:last_bin])*8/ph["seconds"]/1e6 if arrival_bytes is not None else None,
                       "delivered": rx["rx_packets"], "missing_after_drain": missing,
                       "loss_pct": loss, "late_or_missing": deadline_bad,
                       "first_arrival_ms": rx["latency"], "send_lag_ms": tx["send_lag"],
                       "tcp_backpressure_slots": tx["backpressure"],
                       "duplicates": rx["duplicates"], "reordered": rx["reordered"],
                       "send_errors": tx["send_errors"], "emsgsize": tx["emsgsize"]}
                observed.append(row)
                tag = f'{direction}/{proto}/{ph["name"]}'
                if missing < 0 or rx["invalid"] or rx["duplicates"]:
                    failures.append(tag + ": invalid/duplicate delivery or count nonconservation")
                if target and abs(injected / target - 1) > a["injection_tolerance_pct"] / 100:
                    # TCP congestion/backpressure is a transport result, not automatically an injector defect.
                    limits.append(tag + (": TCP_BACKPRESSURED" if proto == "tcp" and tx["backpressure"]
                                         else ": INVALID_INJECTOR_RATE"))
                if tx["send_errors"]:
                    limits.append(tag + ": APP_SEND_ERRORS_OR_MTU_REJECTION")
                if (loss is not None and "max_loss_pct" in a
                    and ph["name"] in a.get("loss_gate_phases",
                        [p["name"] for p in config["phases"]])
                    and loss > a["max_loss_pct"]):
                    failures.append(tag + ": declared loss allowance exceeded")
                if "max_p99_ms" in a and rx["latency"]["n"]:
                    if rx["latency"]["p99_ms"] is None or rx["latency"]["p99_ms"] > a["max_p99_ms"]:
                        failures.append(tag + ": declared one-way p99 allowance exceeded")
    sparse_small={}
    if config["traffic"].get("observe_size_classes",False):
        for direction,sender,receiver in (("c2s",client,server),("s2c",server,client)):
            for pi,ph in enumerate(config["phases"],1):
                tx=sender["stats"]["udp"][pi]
                rx=receiver["stats"]["udp"][pi]
                sent=tx["probe_sent"];arrived=rx.get("probe_rx_first_arrival",0)
                sparse_small[direction+"/"+ph["name"]]={
                    "payload_bytes":64,"offered_hz":config["traffic"]["probe_hz"],
                    "real_sent":sent,"real_first_arrivals":arrived,
                    "missing_after_drain":sent-arrived,
                    "first_arrival_ms":rx.get("sparse_probe_oneway","NOT_OBSERVED"),
                    "reverse_echo_rtt_ms":tx["rtt"],
                    "qualification":"actual 64B 20Hz UDP probes; one-way arrival is NOT echo RTT; no synthetic FEC"
                }
                if sent and (arrived>sent or not isinstance(rx.get("sparse_probe_oneway"),dict)):
                    failures.append(direction+"/"+ph["name"]+": invalid sparse probe first-arrival receipt")
    small_udp={}
    if config["traffic"].get("observe_size_classes",False):
        elapsed=config["warmup_s"]
        for pi,ph in enumerate(config["phases"],1):
            # Guard first 2s / last 1s against netem phase switches.
            lo=round(elapsed*100)+200
            hi=round((elapsed+ph["seconds"])*100)-100
            elapsed+=ph["seconds"]
            for direction, sender, receiver in (("c2s",client,server),("s2c",server,client)):
                tag=direction+"/"+ph["name"]
                tx=sender.get("size_classes",{}).get("udp",[])
                rx=receiver.get("size_classes",{}).get("udp",[])
                small_tx=sender.get("small_udp_tx_bins_10ms")
                small_rx=receiver.get("small_udp_rx_bins_10ms")
                if len(tx)<=pi or len(rx)<=pi or small_tx is None or small_rx is None:
                    failures.append(tag+": missing actual small UDP telemetry")
                    continue
                sent=tx[pi]["small_64_256"]["tx_packets"]
                delivered=rx[pi]["small_64_256"]["rx_packets"]
                missing=sent-delivered
                loss=100*missing/sent if sent else None
                # Compare true small-packet sender/receiver bins shifted by
                # the declared one-way delay; no survivor-only histogram gap.
                shift=round(ph[direction]["delay_ms"]/10)
                gap=(active_gap(small_tx[lo:hi],small_rx[lo+shift:hi+shift])
                     if hi>lo and hi+shift<=len(small_rx) else None)
                stat={"sent":sent,"delivered":delivered,"missing_after_drain":missing,
                      "loss_pct":loss,"first_arrival_ms":rx[pi]["small_64_256"]["latency"],
                      "send_lag_ms":tx[pi]["small_64_256"]["send_lag"],
                      "sender_active_receiver_zero_10ms_gap_ms":gap,
                      "gap_alignment_netem_delay_ms":ph[direction]["delay_ms"],
                      "size_classes":{name:{"tx_packets":tx[pi][name]["tx_packets"],
                                        "rx_packets":rx[pi][name]["rx_packets"],
                                        "p99_ms":rx[pi][name]["latency"]["p99_ms"]}
                                      for name in ("small_64_256","medium_257_899","large_900_plus")}}
                small_udp[tag]=stat
                if sent==0 or missing<0:
                    failures.append(tag+": small UDP cohort missing or nonconserving")
                if (loss is not None and "max_small_udp_loss_pct" in a
                    and ph["name"] in a.get("loss_gate_phases",
                        [p["name"] for p in config["phases"]])
                    and loss>a["max_small_udp_loss_pct"]):
                    failures.append(tag+": small UDP residual exceeds allowance")
                p99=stat["first_arrival_ms"]["p99_ms"]
                if "max_small_udp_p99_ms" in a and (p99 is None or p99>a["max_small_udp_p99_ms"]):
                    failures.append(tag+": small UDP first-arrival p99 exceeds allowance")
    gaps = {}
    for direction, sender, receiver in [("c2s", client, server), ("s2c", server, client)]:
        for proto in ["udp", "tcp"]:
            # Include raw bins in artifact, so variable delay/phase transitions can be reanalyzed.
            gap = active_gap(sender["tx_bins_10ms"][proto], receiver["rx_bins_10ms"][proto])
            gaps[f"{direction}_{proto}"] = gap
            if "max_active_gap_ms" in a and gap > a["max_active_gap_ms"]:
                failures.append(f"{direction}/{proto}: declared active delivery gap allowance exceeded")
    hol = {}
    if a.get("cross_business_hol",False):
        hol, hol_failures, hol_limits = cross_business_hol(config,client,server)
        failures.extend(hol_failures)
        limits.extend(hol_limits)
    for role, data in [("client", client), ("server", server)]:
        if data["capacity_exceeded"] or data["socket_drops"]:
            limits.append(role + ": HARNESS_CAPACITY_LIMITED")
        if data["errors"]:
            # Duplicate probe echoes from deliberate underlay duplication are informational.
            serious = {k: v for k, v in data["errors"].items() if k != "duplicate_or_unknown_probe_echo"}
            if serious:
                limits.append(role + ": " + json.dumps(serious, sort_keys=True))
    if not telemetry["stop_drained_both"]:
        failures.append("public Rust Stop not drained on both sides")
    if not telemetry["effective_config_verified"]:
        failures.append("requested mode/profile/recovery policy has no matching product readback")
    if a["require_retransmission"] and (telemetry["repair_packets"] is None or telemetry["repair_packets"] <= 0):
        failures.append("requested retransmission observation absent")
    if any(row["target_app_mbps"] > 0 and row["delivered"] == 0 for row in observed):
        # Blackout phase can legitimately deliver zero. Recovery is assessed in later phases.
        for row in observed:
            ph = next(p for p in config["phases"] if p["name"] == row["phase"])
            d = ph[row["direction"]]
            lanes = {"game2": 2, "game4": 4}.get(config["product"]["mode"], 1)
            if row["target_app_mbps"] and not row["delivered"] and d["loss_pct"] < 100 and len(d["blackhole_lanes"]) < lanes:
                failures.append(f'{row["direction"]}/{row["phase"]}: no real delivery')
    # Host evidence is separate; high product CPU alone cannot excuse a product bottleneck.
    host_risk = host.get("steal_pct_peak", 0) > 5 or (host.get("cpu_psi_some_mean") or 0) > 20
    if host_risk or host.get("cpu_psi_some_peak", 0) > 20:
        warnings.append("HOST_CONTENTION_OBSERVED; inspect time series, not a capacity verdict from one CPU/PSI number")
    status = "FAIL" if failures else ("INCONCLUSIVE" if limits else "PASS_SCOPED_OBSERVATION")
    return {"result": status, "failures": failures, "limits": limits, "warnings": warnings, "observed": observed,
            "performance_comparison": "INCONCLUSIVE_HOST_CONTENTION" if host_risk else "REQUIRES_MATCHED_VALID_AB_LEGS",
            "active_zero_delivery_ms": gaps, "small_udp": small_udp,
            "loss_gate_phases":a.get("loss_gate_phases",
                [p["name"] for p in config["phases"]]),
            "sparse_small_probes": sparse_small,
            "cross_business_hol": hol,
            "telemetry": telemetry, "host": host,
            "probes": {role: [{"phase": ph["name"], "sent": st["probe_sent"],
                                "received": st["probe_received"], "missing": st["probe_sent"]-st["probe_received"],
                                "rtt_ms": st["rtt"]}
                               for ph, st in zip(phases, d["stats"]["udp"])]
                       for role, d in [("client", client), ("server", server)]},
            "qualification": "Linux public path in this scenario only; NOT Windows/physical/full product",
            "stop_heavier_resource_cases": bool(limits),
            "model": {"assumptions": "IID independent losses, timely repairs, no queue/correlation; NOT acceptance gates",
                      "two_retry_ideal_at_5pct": {"residual": .05**3, "repair_over_first_bytes": .05+.05**2},
                      "RS16_at_5pct": {str(r): fec_residual(16, r, .05) for r in [2, 4, 6, 8, 12, 16, 20]},
                      "actual_partial_blocks_and_repair_timing": "NOT_OBSERVED"}}


def markdown(result):
    lines = ["# Network scenario result", "", "Result: **" + result["result"] + "**", "",
             "Rates are application bytes, first-arrival delay uses the same Linux monotonic clock.", "",
             "|Direction|Protocol|Phase|Offered Mbps|Arrival Mbps|Delivered cohort Mbps|Missing|One-way p99 ms|",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in result.get("observed", []):
        lines.append(f'|{r["direction"]}|{r["protocol"]}|{r["phase"]}|{r["injected_app_mbps"]:.3f}|'
                     f'{r.get("arrival_window_app_mbps")}|{r["cohort_delivered_app_mbps"]:.3f}|{r["missing_after_drain"]}|{r["first_arrival_ms"]["p99_ms"]}|')
    lines += ["", "Failures: " + json.dumps(result.get("failures", [])),
              "", "Limits: " + json.dumps(result.get("limits", [])),
              "", "Warnings: " + json.dumps(result.get("warnings", [])),
              "", "Lost/undelivered records are NOT removed from deadline metrics. Surviving-sample p99 alone is not success."]
    return "\n".join(lines) + "\n"
