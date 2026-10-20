//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "net"
    "net/netip"
    "reflect"
    "testing"

    "golang.org/x/sys/windows"
)

// PLAN013: actual read-only Win32 API roundtrip on a live, non-loopback
// Windows NIC. This test never creates a Wintun, writes DNS, installs WFP
// filters, creates a route, or requires the hosted runner's network control.
func TestPLAN013LiveNativeWFPIPHelperDNSAndCanceledRouteNeverMutatesHost(t *testing.T) {
    ctx := context.Background()
    if err := (N4NativeWFPReader{}).VerifyLayers(); err != nil {
        t.Fatalf("real Windows IPv4+IPv6 WFP engine layer query: %v", err)
    }
    interfaces, err := net.Interfaces()
    if err != nil { t.Fatalf("real Windows interface enumeration: %v", err) }
    var observed bool
    for _, nic := range interfaces {
        if nic.Index <= 0 || nic.Flags&net.FlagUp == 0 || nic.Flags&net.FlagLoopback != 0 { continue }
        index := uint32(nic.Index)
        ipBefore, err := (N4WindowsInterfaceReader{}).ReadIPv4(ctx,index)
        if err != nil { t.Logf("index %d IPv4 IP Helper unavailable: %v", index, err); continue }
        dnsBefore, err := (N4NativeDNSReader{}).Read(ctx,index)
        if err != nil { t.Logf("index %d native DNS unavailable: %v", index, err); continue }
        if dnsBefore.Interface == (windows.GUID{}) || ipBefore.Index != index ||
            ipBefore.MTU < 576 || ipBefore.MTU > 65535 {
            t.Fatalf("actual NIC native API readback invalid index=%d mtu=%d",index,ipBefore.MTU)
        }
        // TEST-NET-only precise lookup: no host route may be adopted as ours.
        key := NativeRouteKey{
            Prefix:netip.MustParsePrefix("192.0.2.241/32"),
            Interface:index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:5,
        }
        _,_,err = (N4WindowsRouteBackend{}).Lookup(ctx,key)
        if err != nil { t.Fatalf("GetIpForwardEntry2 read-only index=%d: %v",index,err) }
        canceled, cancel := context.WithCancel(ctx)
        cancel()
        if err := (N4WindowsRouteBackend{}).CreateIfAbsent(canceled,key); !errors.Is(err,context.Canceled) {
            t.Fatalf("cancelled route Apply unexpectedly reached OS index=%d: %v",index,err)
        }
        if err := (N4WindowsRouteBackend{}).RemoveOwned(canceled,key); !errors.Is(err,context.Canceled) {
            t.Fatalf("cancelled route cleanup unexpectedly reached OS index=%d: %v",index,err)
        }
        ipAfter,err:=(N4WindowsInterfaceReader{}).ReadIPv4(ctx,index)
        if err!=nil {t.Fatalf("post-denial GetIpInterfaceEntry index=%d: %v",index,err)}
        dnsAfter,err:=(N4NativeDNSReader{}).Read(ctx,index)
        if err!=nil {t.Fatalf("post-denial GetInterfaceDnsSettings index=%d: %v",index,err)}
        // The actual OS state, not a mock baseline, must be unchanged
        // after this canceled/no-side-effects test.
        if !reflect.DeepEqual(ipBefore,ipAfter) || !reflect.DeepEqual(dnsBefore,dnsAfter) {
            t.Fatalf("native IPv4/DNS state changed across canceled route operations index=%d",index)
        }
        if err := (N4NativeWFPReader{}).VerifyLayers(); err!=nil {
            t.Fatalf("post-denial WFP layer readback: %v",err)
        }
        observed=true
        t.Logf("PLAN013_WINDOWS_LIVE_WFP_IPHELPER_DNS_ROUTE_READBACK_NO_HOST_MUTATION_PASS interface_index=%d mtu=%d",index,ipAfter.MTU)
        break
    }
    if !observed { t.Fatal("NOT_RUN: no active nonloopback NIC yielded BOTH real IP Helper and DNS native OS snapshots") }
}
