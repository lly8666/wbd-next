"""Pure synthetic H1977 QPC joins. NOT evidence from original Wintun."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_m0_plan029_h1966_steady_qpc import scene,SRC,N,FREQ,PORT
from m0_plan029_h1977_boundary_qpc import analyze

PROXY=52008

def chunk(marker,rows,source):
    a=[]
    for i in range(0,len(rows),96):
        group=rows[i:i+96]
        packed=",".join(":".join(map(str,row)) for row in group)
        a.append(f"{marker}frequency={FREQ} total={len(rows)} dropped=0 "
                 f"chunk={i//96} count={len(group)} rows={packed} source={source}")
    if not rows:
        a.append(f"{marker}frequency={FREQ} total=0 dropped=0 "
                 f"chunk=0 count=0 rows= source={source}")
    return "\n".join(a)

def fixture(retransmit=False):
    log,data=scene()
    if retransmit:
        # Rebuild the actual ingress segment receipts with one genuine
        # repeated TCP sequence in the first non-overlapping app window.
        ing=[]
        for i,(a,b,c) in enumerate(data["direct"]["app_qpc"]):
            ing.append((PORT,1000000+i*1024,1024,a+500,a+700,a+900))
            if i==0:
                ing.append((PORT,1000000,1024,a+1000,a+1010,a+1020))
        leg_start=log.index("PLAN029_H1966_STEADY_LEGS_QPC_FINAL ")
        log=chunk("PLAN029_H1966_STEADY_INGRESS_QPC_FINAL ",
                  ing,"original_rust_wintun_tx_test_only")+"\n"+log[leg_start:]
    tx=[];rx=[];fd=[]
    for i,(a,b,c) in enumerate(data["direct"]["app_qpc"]):
        seq=1000000+i*1024
        tx.append((PROXY,PORT,seq,1024,a+930,a+950))
        rx.append((PROXY,0,seq,1024,a+975,a+990))
        fd.append((PORT,0,a+1000))
    log+="\n"+chunk("PLAN029_H1977_TX_MAILBOX_QPC_FINAL ",
                   tx,"original_native_windows_owner")
    log+="\n"+chunk("PLAN029_H1977_RX_WINTUN_SEND_QPC_FINAL ",
                   rx,"original_native_windows_owner")
    log+="\n"+chunk("PLAN029_H1977_FD_READ_QPC_FINAL ",
                   fd,"original_winsock_events")
    log+=f"\nPLAN029_H1977_PROXY_MAP_FINAL frequency={FREQ} count=1 "
    log+=f"rows={PROXY}:{PORT} source=original_kernel_listener\n"
    return log,data

class H1977BoundedOwnerQpc(unittest.TestCase):
    def test_original_all_windows_boundaries_join(self):
        log,data=fixture()
        r=analyze(log,data,SRC)
        self.assertEqual(r["matched_2048"],N)
        self.assertGreaterEqual(
            r["boundary_gap_us"]["rx_send_return_to_inner_kernel_read"]["p50_us"],0)
        self.assertEqual(r["original_kernel_proxy_port"],PROXY)
        self.assertEqual(r["fd_read_before_kernel_recv_n"],N)
        self.assertEqual(r["severe_ge8ms_windows"],[])
    def test_real_retransmit_rows_retained_without_fake_perf_pass(self):
        log,data=fixture(retransmit=True)
        out=analyze(log,data,SRC)
        self.assertEqual(out["retransmission_windows"],
                         [dict(index=0,seq=1000000,count=1)])
        self.assertIn("DIAGNOSTIC_ONLY",out["status"])
    def test_wrong_proxy_identity_rejected(self):
        log,data=fixture()
        log=log.replace(f"rows={PROXY}:{PORT} source=original_kernel_listener",
                        f"rows={PROXY}:60001 source=original_kernel_listener")
        with self.assertRaisesRegex(RuntimeError,"proxy"):
            analyze(log,data,SRC)
    def test_missing_original_wintun_send_rejected(self):
        log,data=fixture()
        log=log.replace("PLAN029_H1977_RX_WINTUN_SEND_QPC_FINAL",
                        "NOT_THE_ORIGINAL_RX_OWNER")
        with self.assertRaisesRegex(RuntimeError,"chunks missing"):
            analyze(log,data,SRC)
    def test_wrong_original_clock_rejected(self):
        log,data=fixture()
        data["direct"]["qpc_frequency"]+=1
        with self.assertRaisesRegex(RuntimeError,"frequency"):
            analyze(log,data,SRC)
    def test_wrong_kernel_leg_source_rejected(self):
        log,data=fixture()
        # No genuine Wintun source address or original Rust leg matches.
        data["direct"]["source"]="not-the-actual-source"
        with self.assertRaisesRegex(RuntimeError,"original app"):
            analyze(log,data,SRC)

if __name__=="__main__":
    unittest.main()
