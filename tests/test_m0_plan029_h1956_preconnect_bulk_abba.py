"""H1956 exact one SOURCE 4x real 4MiB A/B/B/A joins, fail closed."""
import unittest
from tests.test_m0_plan029_h1955_preconnect_qpc import staged_fixture
from tests.test_m0_plan029_h1948_reply_path_qpc import SHA
from tools.m0_plan029_h1945_reply_qpc import analyze_preconnect_bulk

SIZE=4*1024*1024

def fixture():
    log,scene=staged_fixture()
    marker=[x for x in log.splitlines()
            if x.startswith("PLAN029_H1955_PRECONNECT_AB_QPC_FINAL")][0]
    rows=marker.split("rows=",1)[1].split(" source=",1)[0].split(",")
    # One original cold Direct first, then four 4MiB sessions whose
    # sockets all have distinct original application ports. Keep the
    # remaining 384 real small synthetic events unchanged.
    # Existing H1945/H1955 pure fixture contains EXACTLY 384 small
    # Direct rows and zero cold/bulk rows; inject those five independently.
    # Three ON (cold+first+last 4MiB) and two OFF keep 96/96 small.
    p,mode,start,accepted=rows[0].split(":")
    accept=int(accepted)
    added=[
        f"51000:1:{accept-6000}:{accept-5000}",
        f"51001:1:{accept-5000}:{accept-4000}",
        f"51002:0:{accept-3000}:{accept-3000}",
        f"51003:0:{accept-2000}:{accept-2000}",
        f"51004:1:{accept-2000}:{accept-1000}",
    ]
    rows=added+rows
    newmark=("PLAN029_H1955_PRECONNECT_AB_QPC_FINAL frequency=10000000 "+
             "count=389 early_started=195 early_failed=0 rows="+
             ",".join(rows)+" source=original_rust_direct_test_only")
    log=log.replace(marker,newmark)
    trials=[]
    for i,r in enumerate(rows[1:5]):
        port,mode,start,accepted=map(int,r.split(":"))
        order=["on","off","off","on"]
        assert bool(mode)==(order[i]=="on")
        trials.append({
          "ordinal":i+1,"preconnect":order[i],
          "role":"direct","presented_peer":"198.18.0.1",
          "socket_source":"10.66.0.2","socket_source_port":port,
          "echo_bytes":SIZE,"payload_sha256":"abcd",
          "half_close":True,"app_tcp_nodelay":0,
          "nominal_send_sleep_ms":0.,
          "start_monotonic_s":accepted/10000000-.005,
          "end_monotonic_s":accepted/10000000+.005,
          "elapsed_ms":[120.,350.,140.,125.][i],
          "upload_ms":[55.,295.,75.,60.][i],
          "download_ms":[50.,48.,48.,51.][i],
          "first_reply_wait_ms":3.})
    whole={"source_sha":SHA,"stop":"PASS_BOTH_OWNED",
           "covered_whole_direct_tcp":True,"windows_direct_fakeip":"198.18.0.1",
           "physical_baseline":{"echo_bytes":SIZE,"payload_sha256":"abcd",
                                "elapsed_ms":45.,"app_tcp_nodelay":0},
           "physical_guest":{"received_bytes":[SIZE]*5},
           "udp_sustained_total":700,
           "same_vm_preconnect_bulk":{
               "source_sha":SHA,"status":"PENDING_ORIGINAL_OWNED_STOP_AND_QPC",
               "order":["on","off","off","on"],"all_unpaced_4mib":True,
               "linux_kernel_tcp_connections":5,"trials":trials}}
    return log,scene,whole

class RealBulkPreconnectABBA(unittest.TestCase):
    def test_four_full_sha_fin_and_original_384_small(self):
        log,scene,whole=fixture()
        x=analyze_preconnect_bulk(log,scene,whole,SHA)
        self.assertEqual(x["exact_native_start_accept_join"],4)
        self.assertEqual(x["separate_small_direct_qpc_matches"],384)
        self.assertEqual(x["mode_order"],["on","off","off","on"])
        self.assertEqual(x["means_ms"]["on"]["elapsed_ms"],122.5)
        self.assertEqual(x["means_ms"]["off"]["elapsed_ms"],245)
    def test_stop_must_be_original_owned(self):
        log,scene,whole=fixture();whole["stop"]="PENDING"
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_no_missing_bulk_receipts(self):
        log,scene,whole=fixture();whole["same_vm_preconnect_bulk"]["trials"].pop()
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_no_unrecognized_sha(self):
        log,scene,whole=fixture()
        whole["same_vm_preconnect_bulk"]["trials"][0]["payload_sha256"]="bad"
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_no_switched_mode(self):
        log,scene,whole=fixture()
        whole["same_vm_preconnect_bulk"]["trials"][0]["preconnect"]="off"
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_no_reused_app_port(self):
        log,scene,whole=fixture()
        t=whole["same_vm_preconnect_bulk"]["trials"]
        t[1]["socket_source_port"]=t[0]["socket_source_port"]
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_absent_win_qpc(self):
        log,scene,whole=fixture()
        log="\n".join(x for x in log.splitlines()
                       if "PLAN029_H1955_PRECONNECT_AB_QPC_FINAL" not in x)
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_wrong_session_windows_clock(self):
        log,scene,whole=fixture()
        whole["same_vm_preconnect_bulk"]["trials"][1]["start_monotonic_s"]+=100
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_guest_must_have_five_connections(self):
        log,scene,whole=fixture()
        whole["physical_guest"]["received_bytes"].pop()
        with self.assertRaises(ValueError):analyze_preconnect_bulk(log,scene,whole,SHA)
    def test_source_sha_must_match(self):
        log,scene,whole=fixture()
        with self.assertRaises(ValueError):
            analyze_preconnect_bulk(log,scene,whole,"0"*40)
if __name__=="__main__":unittest.main()
