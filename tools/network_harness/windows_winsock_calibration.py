"""One Windows2022 same-VM real WinSock generator capacity preflight.

Reuses PR #21's strict config and paced UDP/TCP/probe worker. This checks
the harness itself, not the V4 product: all packets stay on 127.0.0.1, no
original TLS, Rust, Wintun, WFP, loss/netem, or tunnel delivery is claimed.
"""
import concurrent.futures
import json
import os
import pathlib
import socket
import sys
import time

from tools.network_harness.config import validate
from tools.network_harness.traffic import Worker

def main():
    if sys.platform != "win32":
        raise RuntimeError("must be native Windows2022 Winsock")
    source = os.environ["GITHUB_SHA"]
    if len(source) != 40:
        raise RuntimeError("exact git SHA missing")
    out = pathlib.Path("result/winsock-calibration")
    out.mkdir(parents=True, exist_ok=True)
    # Concrete fixed scenario and seed. No product-vs-product concurrency.
    # 60s measured, one VM and one measurement job.
    scenario = {
        "version":1, "id":"windows-winsock-preflight-10mbps",
        "owner":"M0", "seed":20261022,
        "product":{"mode":"normal","fec_profile":1,"game_fec":"off"},
        "traffic":{
            "c2s_mbps":10,"s2c_mbps":10,"udp_share":0.5,
            "sizes":[[96,1],[512,2],[1150,2]],
            "tcp_flows":2,"probe_hz":10,"deadline_ms":250,
            "burst_ms":0,"max_packets":1000000,"allow_fragmentation":False,
        },
        "network":{"outer_mtu":1500,"lane_loss":"shared",
            "queue_packets":32768,"netem_rng":"unseeded_recorded"},
        "warmup_s":2, "drain_s":3,
        "phases":[{"name":"steady","seconds":60,
            "c2s":{"loss_pct":0,"delay_ms":0},
            "s2c":{"loss_pct":0,"delay_ms":0}}],
        "acceptance":{"injection_tolerance_pct":3},
        "bundles":{"A":{
            "source":"de5048303d0f7c8d5314660314017b7ffd194fec",
            "run_id":39716823951,"attempt":1,"artifact_id":12399407766,
            "sha256":"cb97ffd9f2e943007cf8c383371ff7bf5f4b822872ae0502201466044c7ec472",
        }},
    }
    cfg = validate(scenario)
    # Distinct peer port, same OS kernel clock, two concurrent directions.
    # No dependency on extra 127/8 aliases, adapters or routing privileges.
    start = time.monotonic_ns() + 6_000_000_000
    client = Worker(cfg,"client","127.0.0.1","127.0.0.1",
                    45701,out/"client.json",start,peer_port=45711)
    server = Worker(cfg,"server","127.0.0.1","127.0.0.1",
                    45711,out/"server.json",start,peer_port=45701)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(server.run),pool.submit(client.run)]
        for future in concurrent.futures.as_completed(futures, timeout=100):
            future.result()
    def measured(path):
        result=json.loads(path.read_text())
        return {proto: result["stats"][proto][1] for proto in ["udp","tcp"]}
    c,s = measured(out/"client.json"),measured(out/"server.json")
    def throughput(tx,rx):
        sent=sum(tx[k]["tx_bytes"] for k in ["udp","tcp"])
        rec=sum(rx[k]["rx_bytes"] for k in ["udp","tcp"])
        # App byte goodput, not tunnel wire throughput.
        return {
            "sender_Mbps":round(sent*8/60/1e6,3),
            "delivered_Mbps":round(rec*8/60/1e6,3),
            "delivery_pct":round(100*rec/max(1,sent),3),
        }
    c2s=throughput(c,s)
    s2c=throughput(s,c)
    output={
        "source_sha":source,"seed":20261022,"measurement_seconds":60,
        "os_platform":"windows-win32","scenario":"winsock-loopback-no-v4",
        "scope":"PR21_WIN_WINSOCK_TRAFFIC_GENERATOR_PREFLIGHT_ONLY",
        "real_v4_public_product":"NOT_RUN",
        "original_go_tls_rust_wintun":"NOT_RUN",
        "loss_1pct_5pct":"NOT_RUN",
        "host_global_wfp_routes":"NOT_RUN",
        "real_host_network_loss":"NOT_RUN",
        "device_packet_counters":"NOT_RUN",
        "OS_queue_drops":"UNKNOWN",
        "c2s":c2s,"s2c":s2c,
        "note":"Loopback worker capacity is not tunneled application goodput.",
    }
    (out/"scope.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,sort_keys=True))
    for name,direction in (("c2s",c2s),("s2c",s2c)):
        if direction["delivered_Mbps"]<8.5 or direction["delivery_pct"]<90:
            raise RuntimeError(f"WinSock PR21 generator {name} saturated below 10Mbps offer; product benchmark denied")
    print("M0_PLAN026_PR21_WINDOWS_WINSOCK_GENERATOR_10MBPS_BIDIRECTIONAL_60S_PREFLIGHT_PASS_NOT_PRODUCT")
if __name__ == "__main__":
    main()
