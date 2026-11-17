//go:build android && arm64 && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "fmt"
    "net"
    "net/netip"
    "os"
    "os/exec"
    "strconv"
    "strings"

    "github.com/lly8666/wobuzhidao/internal/v4productcli/rootjournal"
)

// This runs only AFTER true standard Go TLS/credential/auto-/32,
 // exact OS lease readback, original Rust M4 loop start and FakeTCP DATA
// ownership handoff. The Android APK supplies a ConnectivityManager handle
// and ONE target application UID; uidrange policy NEVER applies to root or
// system processes and CANNOT redirect this same root Go FakeTCP socket.
func androidRootRouteAfterNative(
    c config,tun *ownedTun,authenticatedLease string,
)(func()error,error){
    if c.androidRouteUID==0{return nil,nil}
    if os.Geteuid()!=0{return nil,fmt.Errorf("Android root route requires effective uid 0")}
    if tun==nil||tun.f==nil||c.androidNetworkHandle==0||
       c.androidPhysicalMTU<576||c.androidRouteUID<10000||
       c.androidRouteUID>1999999{
        return nil,fmt.Errorf("Android root route needs a real authenticated session/Network and one app UID")
    }
    lease,err:=netip.ParsePrefix(authenticatedLease)
    if err!=nil||lease.Bits()!=32||!lease.Addr().Is4()||
       lease.Addr().IsUnspecified()||lease.Addr().IsMulticast()||
       tun.cidr!=lease.String(){
        return nil,fmt.Errorf("Android route requires the original Go authenticated /32")
    }
    actual,err:=readOwnedTunIPv4(tun.name)
    if err!=nil||actual!=lease{
        return nil,fmt.Errorf("Android root route refused: kernel TUN lease differs from authenticated /32: %w",err)
    }
    physical,err:=net.InterfaceByName(c.rawInterface)
    if err!=nil||physical==nil||physical.Index<=0||
       physical.MTU!=int(c.androidPhysicalMTU)||
       physical.Flags&net.FlagUp==0{
        return nil,fmt.Errorf("physical Android Network/ifindex/MTU changed before route grant")
    }
    // The physical IPv4 is also from Android LinkProperties, not a magic
    // default route or an interface string chosen by untrusted peer input.
    matched:=false
    addresses,err:=physical.Addrs()
    if err!=nil{return nil,err}
    for _,a:=range addresses{
        p,e:=netip.ParsePrefix(a.String())
        if e==nil&&p.Addr()==c.localIP{matched=true;break}
    }
    if !matched{return nil,fmt.Errorf("physical Network no longer owns the selected local IPv4")}
    runner:=func(args ...string)(string,error){
        command:=exec.Command("ip",args...)
        data,e:=command.CombinedOutput()
        if e!=nil{
            return "",fmt.Errorf("Android owned ip %q: %w (%s)",args,e,
                strings.TrimSpace(string(data)))
        }
        return string(data),nil
    }
    const rootOnlyJournal="/data/local/tmp/wbd-next-root/route-journal.json"
    session,e:=rootjournal.New(runner,rootOnlyJournal,rootjournal.Plan{
        UID:c.androidRouteUID,Tun:tun.name,Lease:lease.String(),
        Underlay:c.rawInterface,NetworkHandle:c.androidNetworkHandle,
        IfIndex:physical.Index,
    })
    if e!=nil{return nil,e}
    // This exact root-only rule is the sole route grant. The kernel
    // readback and fsync'd journal are complete before a positive log.
    fmt.Fprintf(os.Stderr,
        "V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED uid=%d table=%d priority=%d lease=%s physical_ifindex=%d network_handle=%s\n",
        c.androidRouteUID,rootjournal.Table,rootjournal.Priority,
        lease,physical.Index,strconv.FormatUint(c.androidNetworkHandle,10))
    return session.Stop,nil
}
