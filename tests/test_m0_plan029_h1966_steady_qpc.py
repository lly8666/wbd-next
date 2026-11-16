"""Fail-closed synthetic parser tests only; NEVER original Windows evidence."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from m0_plan029_h1966_steady_qpc import analyze

SRC="1"*40
FREQ=10_000_000
PORT=41231
N=2048

def chunk(mark,kind,rows):
    out=[]
    for i in range(0,len(rows),96):
        part=rows[i:i+96]
        blob=",".join(":".join(map(str,r)) for r in part)
        out.append(f"{mark}frequency={FREQ} total={len(rows)} dropped=0 "
                   f"chunk={i//96} count={len(part)} rows={blob} "
                   f"source={kind}")
    return "\n".join(out)

def scene():
    app=[]
    ing=[]
    legs=[]
    for i in range(N):
        a=100_000_000+i*100_000
        app.append([a,a+100,a+60_000])
        ing.append([PORT,1_000_000+i*1024,1024,a+500,a+700,a+900])
        legs.append([PORT,a+1000,a+1100,a+1600,a+35_000,a+35_100,
                     a+40_000,1024,1024,1024,1024,0])
    physical=dict(source=SRC,role="physical",source_ip="172.20.1.1",
        source_port=41230,measured=N,warmup=32,exact_bytes=(N+32)*1024,
        half_close=True,nodelay=1,qpc_frequency=FREQ,
        app_qpc=[[a,b,a+20_000] for a,b,c in app])
    direct={**physical,"role":"direct","source_ip":"10.66.0.2",
        "source_port":PORT,"app_qpc":app}
    data=dict(source_sha=SRC,direct=direct,physical=physical)
    log=chunk("PLAN029_H1966_STEADY_INGRESS_QPC_FINAL ",
              "original_rust_wintun_tx_test_only",ing)+"\n"+chunk(
              "PLAN029_H1966_STEADY_LEGS_QPC_FINAL ",
              "original_rust_tcp_test_only",legs)
    return log,data

class H1966SteadyOriginalQPC(unittest.TestCase):
    def test_exact_byte_window_positive(self):
        log,data=scene()
        report=analyze(log,data,SRC)
        self.assertEqual(report["messages"],N)
        self.assertEqual(report["app_direct_rtt"]["n"],N)
        self.assertEqual(report["wintun_on_packet_to_classification"]["n"],N)
        self.assertIn("no TCP packet count equality",report["sequence_policy"])
        self.assertEqual(report["kernel_inner_read_to_physical_write"]["n"],N)
    def test_missing_rust_real_owner_trace(self):
        log,data=scene()
        with self.assertRaisesRegex(RuntimeError,"no original Rust"):
            analyze(log.split("PLAN029_H1966_STEADY_LEGS_QPC_FINAL ")[0],
                    data,SRC)
    def test_source_must_match(self):
        log,data=scene();data["source_sha"]="2"*40
        with self.assertRaisesRegex(RuntimeError,"SOURCE"):
            analyze(log,data,SRC)
    def test_qpc_frequency_must_match(self):
        log,data=scene();data["direct"]["qpc_frequency"]+=1
        with self.assertRaisesRegex(RuntimeError,"frequency"):
            analyze(log,data,SRC)
    def test_wrong_rust_chunk_count_rejected(self):
        log,data=scene()
        log=log.replace("count=96 ","count=95 ",1)
        with self.assertRaisesRegex(RuntimeError,"chunk row count"):
            analyze(log,data,SRC)
    def test_missing_data_bytes_must_not_join(self):
        log,data=scene()
        # Deliberate split/missing byte: cannot infer the app packet.
        log=log.replace(f"{PORT}:1000000:1024:",f"{PORT}:1000000:1023:",1)
        # First row is the WARMUP-type window placeholder here. The
        # original per-sample Rust receipt must fail rather than interpolate.
        with self.assertRaisesRegex(RuntimeError,"missing or ambiguous"):
            analyze(log,data,SRC)
    def test_wrong_kernel_stage_order_rejected(self):
        log,data=scene()
        log=log.replace(f"{PORT}:100001000:100001100:100001600:",
                        f"{PORT}:100001000:100001700:100001600:",1)
        with self.assertRaisesRegex(RuntimeError,"WinSock event QPC"):
            analyze(log,data,SRC)

if __name__=="__main__":
    unittest.main()
