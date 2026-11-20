#!/usr/bin/env python3
"""H2233 focused 1/5% real TCP investigation, no product protocol edits.

Per-case qdisc deltas are router skb accounting, NOT inferred TCP segment
loss. Original iperf JSON receiver summaries are authoritative goodput.
A branch's failure/capacity qualification never becomes a product PASS.
"""
import json
import os
import pathlib
import re

CASE=re.compile(r"case-(\d{3})-(.+)\.json\Z")
LOSSES=(1,5)
DIRECTIONS=("upload","download")

def load(path):
    return json.loads(path.read_text())

def number(value):
    return isinstance(value,(float,int)) and not isinstance(value,bool)

def safe_ratio(a,b):
    return round(b/a,4) if number(a) and a>0 and number(b) else None

def delta_qdisc(before,after):
    result={}
    for role,direction in (("server","client_to_server"),
                           ("client","server_to_client")):
        try:
            old=next(x for x in before[role]["qdisc"] if x["kind"]=="netem")
            new=next(x for x in after[role]["qdisc"] if x["kind"]=="netem")
            if old.get("handle")!=new.get("handle") or old.get("options")!=new.get("options"):
                raise ValueError("netem changed during case")
            sent=int(new["packets"])-int(old["packets"])
            drops=int(new["drops"])-int(old["drops"])
            if sent<0 or drops<0:raise ValueError("negative netem delta")
            def tx_packets(snapshot):
                link=snapshot[role]["link"][0]
                stats=link.get("stats64") or link.get("stats") or {}
                return int(stats["tx"]["packets"])
            try: link_tx=tx_packets(after)-tx_packets(before)
            except (KeyError,ValueError,IndexError,TypeError):link_tx=None
            if link_tx is not None and link_tx<0:link_tx=None
            total=sent+drops
            result[direction]={
                "netem_emitted_skb":sent,"netem_dropped_skb":drops,
                "netem_drop_pct_of_skb_population":round(100*drops/total,4) if total else None,
                "link_tx_packets_delta":link_tx,
                "netem_emitted_over_link_tx_ratio":round(sent/link_tx,4) if link_tx else None,
                "offload_features_start":before[role].get("offload_features"),
                "offload_features_end":after[role].get("offload_features"),
                "accounting_warning":"Netem sees skb; one skb can represent multiple TCP segments. Not IP packet loss."
            }
        except (KeyError,ValueError,TypeError,StopIteration,IndexError):
            result[direction]={"status":"UNKNOWN_MISSING_OR_CHANGED_KERNEL_QDISC"}
    return result

def socket_mss_readback(case_file,kind):
    """An in-flight genuine Linux ss TCP_INFO MSS joined to iperf local ports.

    Iperf start.tcp_mss is a CLI echo; it is NOT negotiated socket MSS.
    Partial, absent or different-source-port snapshots remain UNKNOWN.
    """
    raw=pathlib.Path(str(case_file)+".stdout.txt")
    snapshot=pathlib.Path(str(case_file)+".tcp-info.txt")
    if not raw.is_file() or not snapshot.is_file():
        return {"status":"UNKNOWN_NOT_SAMPLED","mss":[]}
    try:
        rows=json.loads(raw.read_text())["start"]["connected"]
        ports={int(x["local_port"]) for x in rows}
        if not rows or len(ports)!=len(rows):
            raise ValueError("ports")
        peer="10.248.82.2:5202" if kind=="direct" else "10.66.0.1:5201"
        lines=snapshot.read_text().splitlines()
        found={}
        for n,line in enumerate(lines):
            if peer not in line:continue
            m=re.search(r"\bmss:(\d+)\b"," ".join(lines[n:n+3]))
            if m is None:continue
            for port in ports:
                if re.search(r"\b10\.248\.81\.2:"+str(port)+r"\b",line):
                    found[port]=int(m.group(1))
        return {"status":"REAL_TCP_INFO_ALL_STREAMS" if len(found)==len(ports)
                    else "UNKNOWN_PARTIAL_TCP_INFO",
                "expected_streams":len(ports),"observed_streams":len(found),
                "mss":[found[p] for p in sorted(found)],
                "source":"ss_tinm_real_kernel_socket_by_iperf_local_port"}
    except (OSError,ValueError,TypeError,KeyError):
        return {"status":"UNKNOWN_INVALID_TCP_INFO","mss":[]}

def focused_summary(mode,model,directory):
    path=pathlib.Path(directory)
    expected={"clear-zero-direct-12s-8p-"+d for d in DIRECTIONS}
    for loss in LOSSES:
        for direction in DIRECTIONS:
            for kind in ("direct","wbd"):
                expected.add(f"delay200-loss{loss}-{model}-{kind}-20s-4p-{direction}")
        expected.add(f"delay200-loss{loss}-{model}-wbd-3s-1p-upload")
    rows={}
    unexpected=[]
    for file in sorted(path.glob("case-*.json")):
        match=CASE.fullmatch(file.name)
        if not match or match.group(2) not in expected:
            unexpected.append(file.name);continue
        if match.group(2) in rows:
            unexpected.append(file.name);continue
        try: record=load(file)
        except (OSError,ValueError):record={}
        before=path/("before-"+file.stem+"-relay.json")
        after=path/("after-"+file.stem+"-relay.json")
        if before.is_file() and after.is_file():
            try: qdisc=delta_qdisc(load(before),load(after))
            except (OSError,ValueError,TypeError):qdisc={"status":"UNKNOWN_INVALID_CASE_RECEIPT"}
        else:qdisc={"status":"UNKNOWN_MISSING_CASE_QDISC_SNAPSHOTS"}
        tcp_info=socket_mss_readback(file,record.get("kind",""))
        rows[match.group(2)]={**record,"file":file.name,"router_case_qdisc":qdisc,
            "tcp_mss_observed":tcp_info["mss"],"tcp_info_readback":tcp_info}
    missing=sorted(expected-set(rows))
    failures=sorted(k for k,v in rows.items() if v.get("status")!="PASS_REAL_KERNEL_IPERF3_TCP"
                    or v.get("receiver_goodput_mbps") is None)
    def rate(suffix):
        rec=rows.get(suffix,{})
        return rec.get("receiver_goodput_mbps")
    clear={d:rate("clear-zero-direct-12s-8p-"+d) for d in DIRECTIONS}
    tail=set()
    for file in path.glob("*-relay.json"):
        try:
            snap=load(file)
            for key in ("client","server"):
                state=snap.get("tail_to_"+key,{}).get("tail_path")
                if state:tail.add(state)
        except (OSError,ValueError,AttributeError):pass
    capacity=(all(number(clear[d]) and clear[d]>=800 for d in DIRECTIONS)
              and tail=={"DIRECT_CANDIDATE"})
    comparisons=[]
    for loss in LOSSES:
        for direction in DIRECTIONS:
            a=f"delay200-loss{loss}-{model}-direct-20s-4p-{direction}"
            b=f"delay200-loss{loss}-{model}-wbd-20s-4p-{direction}"
            direct=rows.get(a,{});wbd=rows.get(b,{})
            mss_a=direct.get("tcp_mss_observed") or []
            mss_b=wbd.get("tcp_mss_observed") or []
            requested_a=direct.get("tcp_mss_requested")
            requested_b=wbd.get("tcp_mss_requested")
            comparable=(bool(mss_a and mss_b) and
                        direct.get("tcp_info_readback",{}).get("status")=="REAL_TCP_INFO_ALL_STREAMS" and
                        wbd.get("tcp_info_readback",{}).get("status")=="REAL_TCP_INFO_ALL_STREAMS" and
                        set(mss_a)==set(mss_b)=={1037} and
                        requested_a==requested_b==1037)
            comparisons.append({
                "target_loss_pct":loss,"direction":direction,
                "direct_receiver_goodput_mbps":rate(a),
                "wbd_receiver_goodput_mbps":rate(b),
                "wbd_div_direct_receiver_ratio":safe_ratio(rate(a),rate(b)),
                "direct_sender_mbps":direct.get("sender_mbps"),
                "wbd_sender_mbps":wbd.get("sender_mbps"),
                "direct_mss_observed":mss_a,"wbd_mss_observed":mss_b,
                "direct_mss_source":direct.get("tcp_info_readback"),
                "wbd_mss_source":wbd.get("tcp_info_readback"),
                "mss_requested":1037,
                "actual_mss_readback":"MATCHED" if comparable else "UNKNOWN_OR_MISMATCH",
                "direct_router_qdisc":direct.get("router_case_qdisc"),
                "wbd_router_qdisc":wbd.get("router_case_qdisc"),
                "direct_tcp_retransmits":direct.get("tcp_retransmits"),
                "wbd_tcp_retransmits":wbd.get("tcp_retransmits")
            })
    status=("FAIL_FOCUSED_MISSING_OR_DUPLICATED_CASE" if missing or unexpected else
            "FAIL_FOCUSED_TCP_OR_DELIVERED_GOODPUT" if failures else
            "PASS_FOCUSED_LOW_LOSS_TCP_MATRIX")
    return {
        "schema_version":1,"checkpoint":"H2233","status":status,
        "source_sha":os.environ.get("GITHUB_SHA",""),"run_id":os.environ.get("GITHUB_RUN_ID",""),
        "real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,
        "actual_kernel_forwarding":True,
        "client_native_arch":"x86_64","relay_native_arch":"aarch64",
        "server_native_arch":"x86_64",
        "normal_outer_performative_retransmission":"UNCHANGED_ON",
        "normal_mode":mode,"tc_loss_model":model,
        "focus_loss_percent":[1,5],
        "jitter_profile":os.environ.get("WBD_H2233_JITTER","UNKNOWN"),
        "extra_one_way_delay_ms":200,
        "source_test_scope":"BENCHMARK_ONLY_NO_PRODUCT_DATAPATH_CHANGE",
        "mss_qualification":"PER_CASE_ACTUAL_READBACK_REQUIRED_NOT_JUST_IPERF_ARG",
        "direct_clear_receiver_goodput_mbps":clear,
        "clean_0ms_0pct_direct_8stream_reference_mbps":clear,
        "relay_capacity_qualification":">=800Mbps_BOTH_DIRECTIONS_DIRECT_TAILSCALE" if capacity else
           "INFRA_RELAY_OR_DERP_UNQUALIFIED_DO_NOT_ATTRIBUTE_TO_WBD",
        "tailscale_path_indicators":sorted(tail),
        "expected_cases":len(expected),"actual_cases":len(rows),"missing_case_names":missing,
        "unexpected_case_files":unexpected,"failures":failures,
        "comparisons":comparisons,"raw_cases":[{"case":k,**v} for k,v in sorted(rows.items())],
        "interpretation":"skb netem loss is not independent TCP segment or user-byte loss; receiver goodput, MSS and per-case deltas must be interpreted together",
        "physical_windows_npcap_3sec_crash":"NOT_RUN",
        "product_throughput_causal_improvement":"NOT_TESTED"
    }
