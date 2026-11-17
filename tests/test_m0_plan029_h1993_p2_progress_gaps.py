"""H1995 original WinSock recv 128KiB crossing fix after signed H1993 native FAIL."""
import unittest
from tools.m0_plan029_h1815_p2_real_mixed import normal_tcp_128k_progress_gaps
import json, tempfile
from pathlib import Path

M="PLAN029_H1839_P2_TCP_STAGE "

def log_for(role="baseline",download=None,drop=None):
    down=download or [302,304,306,370,372,374,376,378]
    data=[{"role":role,"phase":"connected","elapsed_ms":3.0}]
    for i,t in enumerate([28,60,92,124,156,188,220,252],1):
        data.append({"role":role,"phase":"upload_progress","bytes":i*131072,"elapsed_ms":t})
    data.extend([
        {"role":role,"phase":"upload_complete","bytes":1048576,"elapsed_ms":256},
        {"role":role,"phase":"half_closed","elapsed_ms":262},
        {"role":role,"phase":"first_reply","elapsed_ms":300},
    ])
    for i,t in enumerate(down,1):
        data.append({"role":role,"phase":"download_progress","bytes":i*131072,"elapsed_ms":t})
    if drop is not None:data.pop(drop)
    return "\n".join(M+json.dumps(x) for x in data)+"\n"

class OriginalProgress(unittest.TestCase):
    def read(self,text,role="baseline"):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"original-client.log"
            p.write_text(text,encoding="utf-8")
            return normal_tcp_128k_progress_gaps(p,role,1024*1024)

    def test_original_1m_paced_milestones_preserve_actual_download_hole(self):
        x=self.read(log_for())
        self.assertEqual(x["bucket_count"],8)
        self.assertEqual(x["upload_max_gap_ms"],32)
        self.assertEqual(x["download_max_gap_ms"],64)
        self.assertEqual(x["download_worst_bucket"],4)
        self.assertTrue(x["upload_includes_4ms_pacing_per_16k"])
        self.assertTrue(x["not_app_rtt_p99_or_rust_cpu"])

    def test_direct_and_physical_are_distinct_original_application_roles(self):
        x=self.read(log_for("direct"),"direct")
        self.assertEqual(x["source"],"ORIGINAL_WINDOWS_APP_EXISTING_128K_RECEIPT")
        with self.assertRaisesRegex(RuntimeError,"unrelated"):
            self.read(log_for("direct"),"baseline")

    def test_missing_milestone_rejected_not_interpolated(self):
        with self.assertRaisesRegex(RuntimeError,"missing/duplicate"):
            self.read(log_for(drop=4))

    def test_duplicate_milestone_rejected(self):
        lines=log_for().splitlines()
        lines.insert(2,lines[2])
        with self.assertRaisesRegex(RuntimeError,"missing/duplicate"):
            self.read("\n".join(lines))

    def test_nonmonotonic_download_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"backwards"):
            self.read(log_for(download=[302,304,306,305,372,374,376,378]))

    def test_real_windows_recv_16k_crossing_milestones(self):
        # Original H1993 failed Action43840543096 artifact14214065842:
        # real physical and FakeIP Direct Windows recv cumulative bytes.
        physical=[134968,268152,399224,530296,661368,792440,923512,1048576]
        direct=[140296,263583,408275,525661,656733,789154,920422,1048576]
        for role,actual in (("baseline",physical),("direct",direct)):
            lines=log_for(role).splitlines()
            replaced=[]
            for line in lines:
                if '"download_progress"' in line:
                    item=json.loads(line[len(M):])
                    index=item["bytes"]//131072-1
                    item["bytes"]=actual[index]
                    line=M+json.dumps(item)
                replaced.append(line)
            result=self.read("\n".join(replaced),role)
            self.assertEqual(result["download_crossing_recv_actual_bytes"],actual)
            self.assertEqual(result["max_allowed_recv_crossing_bytes"],16383)

    def test_download_more_than_one_recv_crossing_rejected(self):
        lines=log_for().splitlines()
        for i,line in enumerate(lines):
            if '"download_progress"' in line:
                item=json.loads(line[len(M):])
                item["bytes"]=131072+16384
                lines[i]=M+json.dumps(item)
                break
        with self.assertRaisesRegex(RuntimeError,"milestone"):
            self.read("\n".join(lines))

    def test_wrong_bucket_bytes_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"milestone"):
            self.read(log_for().replace('"bytes": 524288','"bytes": 524289'))

    def test_not_a_fabricated_2048_or_4m_p99(self):
        with self.assertRaisesRegex(RuntimeError,"only original ordinary"):
            with tempfile.TemporaryDirectory() as folder:
                p=Path(folder)/"record.log";p.write_text(log_for())
                normal_tcp_128k_progress_gaps(p,"baseline",4*1024*1024)

if __name__=="__main__":
    unittest.main()
