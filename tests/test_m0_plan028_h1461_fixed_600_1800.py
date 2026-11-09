import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUST=ROOT/"crates/wbd-engine/src/v4_embedded_go.rs"
FIXTURE=ROOT/"tools/m0-plan028-h1259-five-client-recovery-netns.py"
REPORT=ROOT/"tools/m0-plan028-h1274-30min-report.py"
VERDICT=ROOT/"tools/m0_plan028_h1461_five_client_soak_verdict.py"
WORKFLOW=ROOT/".github/workflows/m0-plan028-h1461-fixed-five-client-600-1800.yml"

class H1461FixedNativeSoaks(unittest.TestCase):
    def test_rust_8_slot_64k_100ms_bounded_urgent_fifo_not_capacity_increase(self):
        s=RUST.read_text()
        self.assertIn("const SHARED_TUN_PENDING_PER_ROUTE:usize=8;",s)
        self.assertIn("const SHARED_TUN_PENDING_BYTES_PER_ROUTE:usize=64*1024;",s)
        self.assertIn("const SHARED_TUN_PENDING_MAX_AGE:Duration=Duration::from_millis(100);",s)
        self.assertIn("let urgent=q.packets.len()>=SHARED_TUN_PENDING_PER_ROUTE-2;",s)
        self.assertIn("let quota=if urgent{SHARED_TUN_DRAIN_PER_ROUTE}else{1};",s)
        self.assertIn("if q.packets.is_empty()",s)
        self.assertIn("if bytes>SHARED_TUN_PENDING_BYTES_PER_ROUTE",s)
        self.assertIn("m0_plan028_h1461_peak75_urgent_fifo_drain_without_larger_queue",s)
        self.assertIn("H1461_URGENT_FIFO_EIGHT_SLOT_BOUNDED_DRAIN_NO_OVERFLOW_PASS",s)
        self.assertIn("m0_plan028_shared_tun_full_a_keeps_b_and_bounded_drop",s)
        self.assertIn("m0_plan028_shared_tun_a_recovers_b_continuous_backlog_drain",s)

    def test_600_duration_true_original_five_clients_no_fake_1800(self):
        s=FIXTURE.read_text()
        self.assertIn('MID600=os.environ.get("WBD_PLAN028_600S_SCENE","")',s)
        self.assertIn('MID600!="capacity75"',s)
        self.assertIn('RATE=(75,2,2,2,2)',s)
        self.assertIn('ROTATION_SECONDS=(3600,3600,3600,3600,3600)',s)
        self.assertIn('("first_wave",90,1/3)',s)
        self.assertIn('("overload",90,1.0)',s)
        self.assertIn('"application_load_seconds":180 if FAST_SCENE else 600 if MID600 else 1800 if LONG_SCENE else 430',s)
        self.assertIn('"simultaneous_stress_seconds":170 if FAST_SCENE else 590 if MID600 else 1790 if LONG_SCENE else 420',s)
        self.assertIn("H1461_NATIVE_X86_FIVE_CLIENT_REAL_600S_CAPACITY75_COMPLETE",s)

    def test_report_distinguishes_600_no_rotation_and_1800_real_handoffs(self):
        s=REPORT.read_text()
        self.assertIn('MID600_PHASES=(("warmup",10,.3)',s)
        self.assertIn('phases=MID600_PHASES if midsix else PHASES',s)
        self.assertIn('assert duration in (600,1800)',s)
        self.assertIn('"NO_ROTATION_BY_DESIGN_600S_ONLY"',s)
        self.assertIn('elif spec["mode"]=="game4":',s)
        self.assertIn("minimum_ten_true_successful_handoffs",s)
        self.assertIn('result["rotation_verdict"]="PASS_ALL_FIVE_SCOPED"',s)
        self.assertIn('assert source["end_ns"]-source["start_ns"]==duration*1_000_000_000',s)

    def test_one_built_product_two_parallel_independent_true_stop_jobs(self):
        s=WORKFLOW.read_text()
        self.assertIn("matrix:",s)
        self.assertIn("seconds: 600",s)
        self.assertIn("seconds: 1800",s)
        self.assertIn("max-parallel: 2",s)
        self.assertIn("fail-fast: false",s)
        self.assertIn("WBD_PLAN028_600S_SCENE:",s)
        self.assertIn("WBD_PLAN028_30M_SCENE:",s)
        self.assertIn("WBD_SHARED_TUN_ROUTE_DIAG:",s)
        self.assertIn("rustup toolchain install 1.85.1",s)
        self.assertIn("H1461_FROZEN_RUST_URGENT_FIFO_8SLOT_AND_LEGACY_ISOLATION_TESTS_PASS",s)
        self.assertIn("wbd-v4-client",s)
        self.assertIn("wbd-v4-server",s)
        self.assertIn("libwbd_engine.so",s)
        self.assertIn("H1461_REAL_ORIGINAL_FIVE_CLIENT_SOAK_BEGIN",s)
        self.assertNotIn("[plan028-win-linux-1800]",s)
        self.assertNotIn("runs-on: windows",s)

    def test_zero_loss_overflow_and_missing_udp_never_rebranded_pass(self):
        s=VERDICT.read_text()
        self.assertIn("ORIGINAL_SERVER_8_SLOT_QUEUE_OVERFLOW_",s)
        self.assertIn("ZERO_LOSS_MISSING_",s)
        self.assertIn("GENERATOR_OR_HOST_FAILED_TO_OFFER_95PCT",s)
        self.assertIn("original_six_owned_final_stop",s)
        self.assertIn("windows_Wintun_L3_1800s",s)
        self.assertIn("H1461_FIVE_CLIENT_NATIVE_TRUE_DURATION_RESULT",s)

if __name__=="__main__":
    unittest.main()
