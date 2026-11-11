"""H1590: Windows ORIGINAL FakeTCP protected-TLS retransmit worker source guard.

This is a source contract only. Neither synthetic packets nor a successful
Go compile can qualify a true signed Windows2025 30% loss native cold TLS.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WIN=ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go"
CLIENT=ROOT/"r0/go_overlay/internal/faketcp/client_association.go"
LINUX=ROOT/"r0/go_overlay/internal/v4productcli/linux.go"
HARNESS=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class OriginalGoColdTLSRealRTO(unittest.TestCase):
    def test_existing_go_faketcp_sender_retransmit_while_real_tls_blocks(self):
        win=WIN.read_text()
        cl=CLIENT.read_text()
        server=LINUX.read_text()
        self.assertIn('case ClientAssociationEstablished:',cl)
        self.assertIn('pending := a.sender.RetransmitDue(now)',cl)
        self.assertIn('Payload: pending.Payload',cl)
        self.assertIn('table.EmitRetransmitDue(now)',server)
        self.assertIn('coldPumpStop:=make(chan struct{})',win)
        self.assertIn('coldPumpDone:=make(chan struct{})',win)
        self.assertIn('coldPumpError:=make(chan error,1)',win)
        self.assertIn('case <-ticker.C:',win)
        self.assertIn('if assoc.State()!=faketcp.ClientAssociationEstablished{return}',win)
        self.assertIn('resent,e:=assoc.EmitRetransmitDue(time.Now())',win)
        self.assertIn('if resent{coldRetransmits++}',win)
        self.assertIn('if e!=nil{\n     select{case coldPumpError<-e:default:}\n     assoc.Close()',win)
        self.assertIn('defer stopColdPump()',win)
        self.assertIn('stopColdPump()\n fmt.Printf("WBD_WINDOWS_ORIGINAL_TLS_COLD_FAKETCP_RETRANSMIT',win)
        self.assertIn('joined_before_Rust_M3=1 source=original_Go_Sender_RTO',win)
        self.assertLess(win.index('coldPumpStop:=make(chan struct{})'),
                        win.index('owner,session,err=realityfront.V4WindowsEstablishOriginalClientOwner'))
        self.assertLess(win.index('stopColdPump()\n fmt.Printf("WBD_WINDOWS_ORIGINAL_TLS_COLD_FAKETCP_RETRANSMIT'),
                        win.index('if err!=nil{return fmt.Errorf("original credential TLS'))
        self.assertIn('Timeout:15*time.Second',win)
        self.assertNotIn('Timeout:45*time.Second',win)
        self.assertIn('WBD_WINDOWS_CLIENT_READY',win)

    def test_true_loss30_source_locked_original_kernel_and_no_fake_readiness(self):
        h=HARNESS.read_text()
        wf=WORKFLOW.read_text()
        ast.parse(h,filename=str(HARNESS))
        self.assertIn('if probe or h1579:',h)
        self.assertIn('s.bind(("10.66.0.1",45941))',h)
        self.assertIn('s.sendto(data,(target,45942))',h)
        self.assertIn('report["h1590_original_windows_cold_tls_real_retransmits"]',h)
        self.assertIn('joined_before_Rust_M3=1 source=original_Go_Sender_RTO',h)
        self.assertIn('marker(OUT/"h1548-windows-alice.log","WBD_WINDOWS_CLIENT_READY",window,160)',h)
        self.assertIn('H1590_REAL_ORIGINAL_FAKETCP_COLD_RETRY_SOURCE_ONLY_NOT_SIGNED_NETWORK',wf)
        self.assertIn('[plan028-h1590-win30-cold-retransmit]',wf)
        self.assertIn('$null -eq $mixed.h1590_original_windows_cold_tls_real_retransmits',wf)
        self.assertIn('H1579 original Windows30 genuine TLS/RustM4/Stop NOT proven',wf)
        self.assertNotIn('fake_reverse_ack',h)
        self.assertNotIn('synthetic_ready',h)


if __name__=="__main__":
    unittest.main()
