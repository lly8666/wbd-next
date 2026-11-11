"""PLAN028 H1573 source-only wiring contract; real Windows+Linux result NOT_RUN.

Mixed protected TLS443 listener, not the standalone Normal listener, must
use each original association's actual SYN presentation for its Rust M4
peer. No pre-TLS lease/persona authority and no new Go hot DATA path.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
NORMAL=ROOT/"r0/go_overlay/internal/v4productcli/linux.go"
MIXED=ROOT/"r0/go_overlay/internal/v4productcli/game_linux.go"
TEST=ROOT/"r0/go_overlay/internal/v4productcli/mixed_peer_persona_linux_test.go"
SCRIPT=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class MixedPersonaOriginalTLS(unittest.TestCase):
    def test_normal_and_game_use_actual_cold_association_only_after_tls(self):
        source=NORMAL.read_text();mixed=MIXED.read_text();unit=TEST.read_text()
        self.assertIn("func originalV4ColdAssocPeerPersona(assoc *faketcp.ServerAssociation",source)
        self.assertIn("profile:=assoc.PeerTCPProfile()",source)
        self.assertIn("if !profile.OriginalSYNPersonaKnown{return fallback,false}",source)
        self.assertIn("faketcp.PacketPersonaWindows11",source)
        self.assertIn("nativePersona,personaKnown:=originalV4ColdAssocPeerPersona(rec.assoc,c.peerPersona)",source)
        self.assertIn("actualPersona,personaKnown:=originalV4ColdAssocPeerPersona(",mixed)
        self.assertIn("lane.Association(),c.peerPersona)",mixed)
        self.assertIn("PeerPersona:actualPersona,Authenticate:originalV4CredentialCheck(c)",mixed)
        self.assertIn("V4_PUBLIC_MIXED_NORMAL_PEER_PERSONA role=server client_port=",mixed)
        self.assertIn("selectedPersona:=c.peerPersona",mixed)
        self.assertIn("gameCfg.PeerPersona=selectedPersona",mixed)
        self.assertIn("stage=game_cohort_peer_persona",mixed)
        self.assertIn("V4_PUBLIC_GAME_MULTI_PEER_PERSONA role=server lanes=",mixed)
        self.assertIn("TestPLAN028MixedServerPerOriginalAssociationSYNPersona",unit)
        self.assertIn("faketcp.MarshalSegment(syn,1,persona)",unit)
        self.assertIn("originalV4ColdAssocPeerPersona(tc.peer,tc.fallback)",unit)
        self.assertLess(mixed.index("normal,_,gameFec,modeErr:=lane.ProtectedMode()"),
                        mixed.index("actualPersona,personaKnown:=originalV4ColdAssocPeerPersona("))
        self.assertLess(mixed.index("key,complete,e:=stageOriginalAuthenticatedGameLane("),
                        mixed.index("selectedPersona:=c.peerPersona"))

    def test_real_native_marker_triggers_four_linux_and_windows_true_persona(self):
        wf=WORKFLOW.read_text();script=SCRIPT.read_text()
        ast.parse(script,filename=str(SCRIPT))
        self.assertIn("[plan028-h1573-mixed-peer-persona]",wf)
        self.assertIn("WBD_PLAN028_MIXED_ASSOC_PERSONA_TEST:",wf)
        self.assertIn("WBD_PLAN028_BOB_NORMAL_DIFFERENTIAL:",wf)
        self.assertIn("H1573-WinLinuxPerSessionPersona-real-BobAuto-c2s-200ms",wf)
        self.assertIn("H1573_ORIGINAL_MIXED_WIN_PERSONA1_LINUX_PERSONA0_TLS_RUST_M4_TRIGGERED",script)
        for x in (
            "client_port=41031 selected=1 cold_syn_known=true",
            "client_port=43031 selected=0 cold_syn_known=true",
            "lanes=2 selected=0 cold_syn_known=true",
            "lanes=4 selected=0 cold_syn_known=true",
        ):
            self.assertIn(x,script)
        self.assertIn('not bob_normal and a.scene=="loss0"',script)
        self.assertIn('h1573_original_persona_M4_triggered',wf)
        self.assertIn("h1572_bob_mode_differential -ne 'unchanged_fec_auto'",wf)
        self.assertIn('["mixed-loss0"]',wf)
        self.assertIn('"600s_outer_capacity": (',script)
        self.assertIn('"NOT_RUN_H1579_SHORT_30PCT_COLD_TLS" if h1579 else',script)
        self.assertIn('"NOT_RUN_H1581_TRUE_150S_FIVE_NATIVE" if h1581 else',script)
        self.assertIn('"NOT_RUN_H1574_TRUE_150S_FIVE_NATIVE" if l1_150 else',script)
        self.assertIn('"NOT_RUN_H1565_SHORT_FIRST_FAULT" if probe else "PENDING_H1548"',script)
        self.assertIn("Windows_original_WAL_leftover",script)
        self.assertIn("V4_PUBLIC_SHARED_TUN_STOP generation=",script)


if __name__=="__main__":
    unittest.main()
