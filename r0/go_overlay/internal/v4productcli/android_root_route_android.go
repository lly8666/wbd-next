//go:build android && (arm64 || amd64) && cgo && wbd_v4_embedded_go

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
// and one exact app UID or up to eight validated app UIDs. uidrange policy
// NEVER applies to root/system or this original Go FakeTCP socket.
func androidRootRouteAfterNative(
    c config,tun *ownedTun,authenticatedLease string,
)(func()error,error){
    if !c.androidRouteAllApps&&c.androidRouteUID==0&&len(c.androidRouteUIDs)==0{return nil,nil}
    if os.Geteuid()!=0{return nil,fmt.Errorf("Android root route requires effective uid 0")}
    if tun==nil||tun.f==nil||c.androidNetworkHandle==0||
       c.androidPhysicalMTU<576{
        return nil,fmt.Errorf("Android root route needs a real authenticated session/Network")
    }
    if c.androidRouteAllApps{
        if c.androidRouteUID!=0||len(c.androidRouteUIDs)!=0||
            !rootjournal.ValidAllAppExclusions(c.androidRouteExcludeAppIDs){
            return nil,fmt.Errorf("Android all-app routing requires canonical own+manager app IDs")
        }
    }else if len(c.androidRouteUIDs)>0{
        if c.androidRouteUID!=0||!rootjournal.ValidGroupUIDs(c.androidRouteUIDs){
            return nil,fmt.Errorf("Android group route must contain 2..8 distinct sorted ordinary App UIDs")
        }
    }else if c.androidRouteUID<10000||c.androidRouteUID>1999999{
        return nil,fmt.Errorf("Android single route UID must identify an ordinary App")
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
    if c.androidRouteAllApps{
        full,e:=rootjournal.NewAllApps(runner,rootOnlyJournal,rootjournal.AllAppPlan{
            ExcludedAppIDs:append([]int(nil),c.androidRouteExcludeAppIDs...),
            Tun:tun.name,Lease:lease.String(),ServerIP:c.peerIP.String(),
            Underlay:c.rawInterface,
            NetworkHandle:c.androidNetworkHandle,IfIndex:physical.Index,
        })
        if e!=nil{return nil,e}
        // Exact server-IP exclusion in the private FIB is verified,
        // but the next Android netd physical route is not yet qualified.
        fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_PEER_THROW_ROUTE_READBACK role=client")
        // Published only AFTER all bounded kernel uidrange rules (every
        // ordinary App UID in the 20 supported profiles, excluding owner
        // and KSU Manager IDs) have exact OS readback.
        fmt.Fprintf(os.Stderr,
            "V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED mode=all_apps table=%d lease=%s physical_ifindex=%d network_handle=%s\n",
            rootjournal.Table,lease,physical.Index,
            strconv.FormatUint(c.androidNetworkHandle,10))
        return full.Stop,nil
    }
    if len(c.androidRouteUIDs)>0{
        group,e:=rootjournal.NewGroup(runner,rootOnlyJournal,rootjournal.GroupPlan{
            UIDs:append([]int(nil),c.androidRouteUIDs...),
            Tun:tun.name,Lease:lease.String(),Underlay:c.rawInterface,
            NetworkHandle:c.androidNetworkHandle,IfIndex:physical.Index,
        })
        if e!=nil{return nil,e}
        // This receipt is printed only AFTER the entire owned kernel
        // group receives positive readback. Not a fake per-App ACK.
        var uidText []string
        for _,uid:=range c.androidRouteUIDs{
            uidText=append(uidText,strconv.Itoa(uid))
        }
        fmt.Fprintf(os.Stderr,
            "V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED uids=%s table=%d priorities=%d..%d lease=%s physical_ifindex=%d network_handle=%s\n",
            strings.Join(uidText,","),rootjournal.Table,rootjournal.Priority,
            rootjournal.Priority+len(c.androidRouteUIDs)-1,
            lease,physical.Index,strconv.FormatUint(c.androidNetworkHandle,10))
        return group.Stop,nil
    }
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
