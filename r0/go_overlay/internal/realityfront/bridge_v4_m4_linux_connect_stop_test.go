//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe

package realityfront

import (
    "net"
    "os"
    "os/exec"
    "strings"
    "testing"
)

// M4 source-owned integration witness. The M0-owned original authenticated
// Linux source/RS16/real client TUN fixture performs the REAL connection,
// a deliberately lost raw-kernel FEC source, original Go release-client RX,
// actual M4 native TUN UDP delivery, native Stop/join, repeated Stop and
// post-Stop feedback/RX reject. Reuse that exact real traffic path: a second
// synthetic/mock Connect implementation would falsely qualify the product.
//
// This test runs ONLY if M0 integrates this exact M4 file in the same pinned
// original-Go Linux combined workflow, and selects it inside a disposable
// netns. It must never infer success from a standalone call or skip.
func TestM4Plan012OriginalGoLinuxConnectStopOwnedCleanup(t *testing.T) {
    if os.Getenv("WBD_REAL_TUN")!="1" ||
        os.Getenv("WBD_M0_FEC2_CONTINUOUS")!="1" {
        t.Skip("M4_PLAN012_REAL_GO_STOP_NOT_RUN: isolated combined netns only")
    }
    // Existing M0 original Go helper fails on TLS capability/epoch, lost
    // source not recovered by RS16, unauthenticated client RX, missing TUN
    // UDP, incomplete Rust Stop, stale RX/feedback, or leaked server/client
    // TUN interfaces. No second FEC simulator or acceptance path.
    realOriginalGoFec2LinuxMode(t, FecV2Fixed)

    for _,device:=range []string{"wbdfeccont0","wbdfeccli0"} {
        if _,err:=net.InterfaceByName(device);err==nil {
            t.Fatalf("M4 original Go Stop retained interface %s",device)
        }
        output,err:=exec.Command("ip","-4","route","show","dev",device).CombinedOutput()
        if err!=nil {
            t.Fatalf("M4 isolated native route cleanup readback %s: %v %s",
                device,err,output)
        }
        if strings.TrimSpace(string(output))!="" {
            t.Fatalf("M4 Stop left owned capture route for %s: %s",device,output)
        }
    }
    t.Log("M4_PLAN012_ORIGINAL_GO_TLS_FEC_MISSING_SOURCE_REAL_CLIENT_TUN_UDP_REPEATED_STOP_STALE_RX_ROUTE_FD_CLEANUP_PASS")
}
