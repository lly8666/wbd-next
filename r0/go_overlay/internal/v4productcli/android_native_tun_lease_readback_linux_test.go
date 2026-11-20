//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "net"
    "net/netip"
    "testing"
)

// A41: exact production Android TUN getifaddrs parser, on the original
// Go package assembled into BOTH genuine Android and Linux CLI binaries.
// The host doesn't pretend to be an Android device/TUN; interface
// enumeration itself must be confirmed in the next user device receipt.
func TestA41AndroidOriginalOwnedTunIPv4NativeGetifaddrs(t *testing.T){
    ipv4:=func(ip string,prefix int)net.Addr{
        return &net.IPNet{IP:net.ParseIP(ip),Mask:net.CIDRMask(prefix,32)}
    }
    ipv6:=func()net.Addr{
        return &net.IPNet{IP:net.ParseIP("fe80::1234"),Mask:net.CIDRMask(64,128)}
    }
    expected:=netip.MustParsePrefix("10.66.0.3/32")
    for _,a:=range [][]net.Addr{{ipv4("10.66.0.3",32)},{ipv6(),ipv4("10.66.0.3",32)}}{
        p,err:=originalV4OwnedTunIPv4FromNativeAddrs(a)
        if err!=nil||p!=expected{t.Fatalf("real Go native /32 accepted incorrect %s, %v",p,err)}
    }
    for _,a:=range [][]net.Addr{
        nil,{}, {ipv6()},{ipv4("10.66.0.3",24)},
        {ipv4("10.66.0.3",32),ipv4("10.66.0.4",32)},
        {ipv4("0.0.0.0",32)},{ipv4("224.0.0.1",32)},
    }{
        if p,err:=originalV4OwnedTunIPv4FromNativeAddrs(a);err==nil{
            t.Fatalf("invalid actual kernel TUN IPv4 accepted: %s",p)
        }
    }
    // The actual selector in Android readOwnedTunIPv4 must use
    // net.InterfaceByName+Interface.Addrs, never reparse shell JSON.
    t.Log("Original Go native Android TUN readback parses exact /32 only")
}
