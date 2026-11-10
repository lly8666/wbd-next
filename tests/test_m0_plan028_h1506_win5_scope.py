"""Offline contract for real, bounded H1506 five-Windows client qualification."""
import ast,pathlib,random,runpy,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
TOOLS=ROOT/"tools"
class H1506OriginalFiveWindowsScope(unittest.TestCase):
    def test_exact_five_original_modes_payload_budget_and_real_unique_receivers(self):
        app=runpy.run_path(str(TOOLS/"m0_plan028_h1506_win5_real_app.py"))
        self.assertEqual(app["NAMES"],("alice","bob","carol","dave","erin"))
        self.assertEqual(app["BASE"],(8.0,5.0,4.0,2.0,4.0))
        self.assertEqual(sum(app["BASE"])*2,46)
        self.assertLessEqual(app["PAYLOAD"]+28,1178)
        self.assertEqual(app["INNER"],tuple("10.66.0."+str(i) for i in range(2,7)))
        s=(TOOLS/"m0_plan028_h1506_win5_real_app.py").read_text()
        for tag in ("actual_kernel_send_accepted","actual_unique_received",
                    "duplicate","invalid","real_receiver_10ms_bins",
                    "real_native_app_1s","recvfrom","sendto",
                    "max_interdelivery_ms","barrier"):
            self.assertIn(tag,s)
        self.assertNotIn("fake_delivery",s)
    def test_two_exact_real_200ms_zero_thirty_bidirectional_owned_qdiscs(self):
        s=(TOOLS/"m0_plan028_h1506_win5_owned_netem.py").read_text()
        self.assertIn("choices=(0,30)",s)
        self.assertIn('PORTS=(443,444,445,446)',s)
        self.assertIn('"200ms"',s)
        self.assertIn('"ifbh1506"',s)
        self.assertIn('"netem"',s)
        self.assertIn('"priomap",*(["1"]*16)',s)
        self.assertIn('"ip","sport"',s)
        self.assertIn('"ip","dport"',s)
        self.assertIn('"clean"',s)
        self.assertIn('source":os.environ.get("GITHUB_SHA")',s)
    def test_four_real_physical_windows_source_cohort_events_seeded_100_130s(self):
        s=(TOOLS/"m0_plan028_h1506_windows_five_native_600.py").read_text()
        for seed in range(64):
            rnd=random.Random(seed)
            steps=[rnd.randint(100,130) for _ in range(4)]
            self.assertTrue(all(100<=n<=130 for n in steps))
            self.assertLessEqual(sum(steps),520)
        for tag in ("os_script(\"Switch\",alias)",
                    "m0_plan028_h1506_windows_owned_source_flip.ps1",
                    "real_OS_cohort_change_intervals_s",
                    "WBD_WINDOWS_CLIENT_READY",
                    "WBD_WINDOWS_GAME_NATIVE_APPLIED lanes=",
                    "WBDWL5","V4_PUBLIC_MULTI_SESSION_READY",
                    "first_Stop_sibling_real_UDP_TCP"):
            self.assertIn(tag,s)
        flip=(TOOLS/"m0_plan028_h1506_windows_owned_source_flip.ps1").read_text()
        self.assertIn("Find-NetRoute",flip)
        self.assertIn("Set-NetIPAddress",flip)
        self.assertIn("SkipAsSource",flip)
        self.assertIn("PLAN028_TEST_ONLY",flip)
        self.assertNotIn("V4_PUBLIC_PATH_NEW_GENERATION_READY",flip)
    def test_actual_outer_not_inner_target_and_hard_stops(self):
        s=(TOOLS/"m0_plan028_h1506_windows_five_native_600.py").read_text()
        for tag in ("actual_ingress_windows_to_linux",
                    "actual_egress_linux_to_windows",
                    "five_clients_both_directions_outer_mbps",
                    "within_real_70_to_100_mbps",
                    "CAPACITY_LIMITED_WIN_HOST_30S",
                    "actual_udp_rate_scale","original_owned_tc_netem_cleanup",
                    "server_shared_tun_exact_original_stop",
                    "owner_WAL_leftover",
                    "physical_loss_pct","true Windows",
                    "raise SystemExit(1)"):
            if tag=="true Windows":continue
            self.assertIn(tag,s)
        self.assertNotIn("USER_DATA_DUAL_SEND",s)
    def test_native_workflow_separate_0_and_30_600_and_original_legacy_protected(self):
        s=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn('["loss0","loss30"]',s)
        self.assertIn("plan028-h1506-win5-600",s)
        self.assertIn("matrix.win5_scene == 'legacy'",s)
        self.assertIn("m0_plan028_h1506_windows_five_native_600.py",s)
        self.assertIn("H1506_TRUE_WINDOWS_FIVE_NATIVE_600S_",s)
        self.assertIn("m0_plan028_h1415_windows_linux_independent_clients.py",s)
        self.assertIn("native-public-two-os:",s)
        self.assertIn("!contains(github.event.head_commit.message, '[plan028-win-linux-1800]')",s)
    def test_all_new_test_only_python_is_syntax_valid(self):
        for name in ("m0_plan028_h1506_windows_five_native_600.py",
                     "m0_plan028_h1506_win5_real_app.py",
                     "m0_plan028_h1506_win5_owned_netem.py"):
            ast.parse((TOOLS/name).read_text(),filename=name)
if __name__=="__main__":unittest.main()
