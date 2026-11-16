"""H1955 signed original SYN-start A/B: exact 384 Windows app joins."""
import unittest
from tests.test_m0_plan029_h1953_prewrite_qpc import fixture
from tools.m0_plan029_h1945_reply_qpc import analyze_preconnect
from tests.test_m0_plan029_h1948_reply_path_qpc import SHA

def staged_fixture():
    log,scene=fixture()
    row=[x for x in log.splitlines()
         if "PLAN029_H1953_PREWRITE_QPC_FINAL" in x][0]
    records=row.split("rows=",1)[1].split(" source=",1)[0].split(",")
    pre=[]
    on=0
    for j,item in enumerate(records):
        parts=item.split(":")
        port,accepted=parts[:2]
        enabled=int(j%2==0)
        if enabled:on+=1
        started=int(accepted)-1000 if enabled else int(accepted)
        pre.append(f"{port}:{enabled}:{started}:{accepted}")
    mark=("PLAN029_H1955_PRECONNECT_AB_QPC_FINAL frequency=10000000 "+
          "count="+str(len(pre))+" early_started="+str(on)+
          " early_failed=0 rows="+",".join(pre)+
          " source=original_rust_direct_test_only")
    return log+"\n"+mark,scene

class SignedPreconnectAB(unittest.TestCase):
    def test_exact_384_per_echo_policy_interleaved(self):
        log,scene=staged_fixture()
        report=analyze_preconnect(log,scene,SHA)
        self.assertEqual(report["matched_direct_events"],384)
        for policy in ("fin_first","payload_first"):
            self.assertEqual(report["policies"][policy]["on"]["n"],96)
            self.assertEqual(report["policies"][policy]["off"]["n"],96)
    def test_mark_missing(self):
        log,scene=staged_fixture()
        with self.assertRaises(ValueError):
            analyze_preconnect(log.rsplit("\n",1)[0],scene,SHA)
    def test_duplicate_marker(self):
        log,scene=staged_fixture();log+="\n"+log.splitlines()[-1]
        with self.assertRaises(ValueError):analyze_preconnect(log,scene,SHA)
    def test_bad_timestamp(self):
        log,scene=staged_fixture()
        mark=log.splitlines()[-1]
        start=mark.split("rows=",1)[1].split(",")[0]
        port,enable,earliest,accept=start.split(":")
        changed=f"{port}:{enable}:{int(accept)+2}:{accept}"
        log=log.replace(start,changed,1)
        with self.assertRaises(ValueError):analyze_preconnect(log,scene,SHA)
    def test_false_off_early(self):
        log,scene=staged_fixture()
        mark=log.splitlines()[-1]
        second=mark.split("rows=",1)[1].split(",")[1]
        port,enable,start,accept=second.split(":")
        self.assertEqual(enable,"0")
        log=log.replace(second,f"{port}:0:{int(accept)-1}:{accept}",1)
        with self.assertRaises(ValueError):analyze_preconnect(log,scene,SHA)
    def test_missing_one_result(self):
        log,scene=staged_fixture()
        mark=log.splitlines()[-1]
        pre=mark.split("rows=",1)[1].split(" source=",1)[0].split(",")
        log=log.replace(pre[0]+",","",1)
        with self.assertRaises(ValueError):analyze_preconnect(log,scene,SHA)
    def test_early_failed_no_silent_fallback(self):
        log,scene=staged_fixture()
        log=log.replace("early_failed=0","early_failed=1")
        with self.assertRaises(ValueError):analyze_preconnect(log,scene,SHA)
    def test_source_lock(self):
        log,scene=staged_fixture()
        with self.assertRaises(ValueError):
            analyze_preconnect(log,scene,"0"*40)
    def test_freq_mismatch(self):
        log,scene=staged_fixture()
        log=log.replace("PLAN029_H1955_PRECONNECT_AB_QPC_FINAL frequency=10000000",
                        "PLAN029_H1955_PRECONNECT_AB_QPC_FINAL frequency=10000002")
        with self.assertRaises(ValueError):analyze_preconnect(log,scene,SHA)
if __name__=="__main__":unittest.main()
