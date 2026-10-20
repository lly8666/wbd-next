//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe

package realityfront

import (
    "bytes"
    "net"
    "os"
    "os/exec"
    "strings"
    "testing"
)

// Test-only source-owned owned-state readback. Entirely inside M0's disposable
// netns; no commands run in the shipping original Go Connect/Stop product.
func m4Plan012NetnsIPv4Snapshot(t *testing.T) (routes, rules []byte) {
    t.Helper()
    get:=func(args ...string) []byte {
        t.Helper()
        out,err:=exec.Command("ip",args...).CombinedOutput()
        if err!=nil {t.Fatalf("isolated IPv4 %v readback: %v %s",args,err,out)}
        return bytes.TrimSpace(out)
    }
    return get("-4","route","show","table","all"),get("-4","rule","show")
}

func m4Plan012TunFDReadback(t *testing.T) int {
    t.Helper()
    entries,err:=os.ReadDir("/proc/self/fd")
    if err!=nil {t.Fatalf("owned /proc/self/fd readback: %v",err)}
    count:=0
    for _,entry:=range entries {
        target,err:=os.Readlink("/proc/self/fd/"+entry.Name())
        if os.IsNotExist(err) {continue} // fd closed between readdir/readlink
        if err!=nil {t.Fatalf("owned descriptor %s readlink: %v",entry.Name(),err)}
        if strings.HasPrefix(target,"/dev/net/tun") {count++}
    }
    return count
}

// M4 source-owned integration witness, NOT an alternate V4/TLS/FEC producer.
// M0 original-Go code does real credential TLS, deliberate loss of the ACTUAL
// kernel FEC source, RS16 repair, M4 ScopedTunSink UDP delivery, authenticated
// reverse M2, Stop twice and reject old-generation RX/feedback. This test
// strengthens that ORIGINAL fixture with independent OS cleanup readback.
//
// The named test must be source-locked into the existing M0 combined workflow
// and run in its dedicated Linux netns; a skip is NOT proof of completion.
func TestM4Plan012OriginalGoLinuxConnectStopOwnedCleanup(t *testing.T) {
    if os.Getenv("WBD_REAL_TUN")!="1" ||
        os.Getenv("WBD_M0_FEC2_CONTINUOUS")!="1" {
        t.Skip("M4_PLAN012_REAL_GO_STOP_NOT_RUN: isolated combined netns only")
    }
    beforeRoutes,beforeRules:=m4Plan012NetnsIPv4Snapshot(t)
    beforeTunFDs:=m4Plan012TunFDReadback(t)

    // Calls the EXACT M0 original-Go private authenticated network fixture;
    // no simulated FEC/Stop/UDP or second packet sender. The helper fails if
    // any app delivery, missing-source RS16 recovery or Stop check fails.
    realOriginalGoFec2LinuxMode(t,FecV2Fixed)

    afterRoutes,afterRules:=m4Plan012NetnsIPv4Snapshot(t)
    afterTunFDs:=m4Plan012TunFDReadback(t)
    if !bytes.Equal(beforeRoutes,afterRoutes) {
        t.Fatalf("M4 Stop changed original netns IPv4 route table: before=%q after=%q",
            beforeRoutes,afterRoutes)
    }
    if !bytes.Equal(beforeRules,afterRules) {
        t.Fatalf("M4 Stop changed original netns IPv4 policy routing: before=%q after=%q",
            beforeRules,afterRules)
    }
    if afterTunFDs!=beforeTunFDs {
        t.Fatalf("M4 Stop leaked or closed foreign TUN fd: baseline=%d after=%d",
            beforeTunFDs,afterTunFDs)
    }
    for _,device:=range []string{"wbdfeccont0","wbdfeccli0"} {
        if _,err:=net.InterfaceByName(device);err==nil {
            t.Fatalf("M4 original Go Stop retained interface %s",device)
        }
        if strings.Contains(string(afterRoutes),"dev "+device) {
            t.Fatalf("M4 Stop left owned capture route for %s: %s",device,afterRoutes)
        }
    }
    t.Log("M4_PLAN012_ORIGINAL_GO_TLS_FEC_MISSING_SOURCE_REAL_CLIENT_TUN_UDP_REPEATED_STOP_STALE_RX_ROUTE_FD_CLEANUP_PASS")
}
