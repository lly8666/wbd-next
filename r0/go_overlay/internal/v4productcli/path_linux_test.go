//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "encoding/binary"
    "fmt"
    "net"
    "net/netip"
    "testing"
    "time"

    "golang.org/x/sys/unix"
)

func TestPLAN028PhysicalRouteAuthorityNotVPNOrTextIntent(t *testing.T){
    remote:=netip.MustParseAddr("203.0.113.44")
    fakeInterface:=func(name string)(*net.Interface,error){
        if name=="vethA"{return &net.Interface{Name:"vethA",Index:31,MTU:1280},nil}
        return nil,net.ErrClosed
    }
    raw:=[]byte("[{\"dst\":\"203.0.113.44\",\"gateway\":\"192.0.2.1\",\"dev\":\"vethA\",\"prefsrc\":\"192.0.2.22\"}]")
    good,err:=parseOriginalRouteJSON(raw,remote,"wbd-tun",fakeInterface)
    if err!=nil||!good.valid()||good.iface!="vethA"||good.ifindex!=31||
       good.mtu!=1280||good.src!=netip.MustParseAddr("192.0.2.22")||
       good.gateway!=netip.MustParseAddr("192.0.2.1"){
        t.Fatalf("actual IPv4 route not parsed: %+v %v",good,err)
    }
    for _,bad:=range []string{
       "[{\"dev\":\"wbd-tun\",\"prefsrc\":\"192.0.2.22\"}]",
       "[{\"dev\":\"vethA\",\"prefsrc\":\"0.0.0.0\"}]",
       "[{\"dev\":\"vethA\",\"prefsrc\":\"192.0.2.22\",\"type\":\"unreachable\"}]",
       "[{\"dev\":\"vethA\",\"prefsrc\":\"192.0.2.22\"},{\"dev\":\"vethA\",\"prefsrc\":\"192.0.2.23\"}]",
       "[{\"dev\":\"vethA\",\"prefsrc\":\"192.0.2.22\",\"gateway\":\"2001:db8::1\"}]",
       "[{\"dev\":\"wbd-tun\",\"prefsrc\":\"192.0.2.22\",\"type\":\"local\"}]",
    }{
        if _,err:=parseOriginalRouteJSON([]byte(bad),remote,"wbd-tun",fakeInterface);err==nil{
            t.Fatalf("untrusted/loopback route accepted: %s",bad)
        }
    }
}

// Route metrics are kernel-originated and override an otherwise healthy
// 1500-byte physical device on the exact numeric server destination.
func TestPLAN028RouteMTUMetricOverridesPhysicalInterface(t *testing.T){
    remote:=netip.MustParseAddr("203.0.113.44")
    lookup:=func(name string)(*net.Interface,error){
        if name=="ethA"{return &net.Interface{Name:name,Index:12,MTU:1500},nil}
        return nil,net.ErrClosed
    }
    route:=func(mtu int)[]byte{
        return []byte(fmt.Sprintf(`[{"dst":"203.0.113.44","dev":"ethA","prefsrc":"192.0.2.22","mtu":%d}]`,mtu))
    }
    got,err:=parseOriginalRouteJSON(route(1280),remote,"wbd-tun",lookup)
    if err!=nil||got.mtu!=1280{t.Fatalf("real route MTU not applied: %+v %v",got,err)}
    got,err=parseOriginalRouteJSON(route(1600),remote,"wbd-tun",lookup)
    if err!=nil||got.mtu!=1500{t.Fatalf("interface cap bypassed: %+v %v",got,err)}
    for _,mtu:=range []int{-1,575,65536}{
        if _,err=parseOriginalRouteJSON(route(mtu),remote,"wbd-tun",lookup);err==nil{
            t.Fatalf("illegal route mtu %d accepted",mtu)
        }
    }
    got,err=parseOriginalRouteJSON([]byte(`[{"dst":"203.0.113.44","dev":"ethA","prefsrc":"192.0.2.22"}]`),remote,"wbd-tun",lookup)
    if err!=nil||got.mtu!=1500{t.Fatalf("no metric broke interface fallback: %+v %v",got,err)}
}

func TestPLAN028RouteMTUCarriesIntoAuthenticatedNativeBudget(t *testing.T){
    // Candidate B path is 1280 while physical NIC still advertises 1500.
    // The post-TLS callback MUST preserve the stricter cold budget.
    cases:=[]struct{iface,path,want int}{
        {1500,1280,1280},
        {1280,1500,1280},
        {1500,0,1500},
        {1500,1500,1500},
    }
    for _,tc:=range cases{
        got,err:=originalNativeDeviceMTU(config{underlayBudgetMTU:tc.path},tc.iface)
        if err!=nil||got!=tc.want{
            t.Fatalf("authenticated native MTU iface=%d path=%d: got=%d err=%v want=%d",
                tc.iface,tc.path,got,err,tc.want)
        }
    }
    for _,tc:=range []struct{iface,path int}{
        {1500,575},{1500,65536},{575,1280},
    }{
        if _,err:=originalNativeDeviceMTU(config{underlayBudgetMTU:tc.path},tc.iface);err==nil{
            t.Fatalf("invalid path/interface MTU accepted: %+v",tc)
        }
    }
}

func TestPLAN028NativePathNotifications200msQuiet500msAbsolute(t *testing.T){
    start:=time.Unix(1000,0)
    var c originalLinuxCoalescer
    if c.remaining(start)!=-1{t.Fatal("unarmed path coalescer")}
    c.push(start)
    if c.remaining(start)!=200*time.Millisecond{t.Fatal("first OS path event not 200ms")}
    c.push(start.Add(190*time.Millisecond))
    if c.remaining(start.Add(200*time.Millisecond))!=190*time.Millisecond{
        t.Fatal("repeated events did not quiet coalesce")
    }
    for elapsed:=210*time.Millisecond;elapsed<=490*time.Millisecond;elapsed+=20*time.Millisecond{
        c.push(start.Add(elapsed))
    }
    if remaining:=c.remaining(start.Add(495*time.Millisecond));remaining!=5*time.Millisecond{
        t.Fatalf("burst postponed beyond hard 500ms deadline: %v",remaining)
    }
    if c.remaining(start.Add(500*time.Millisecond))!=0{
        t.Fatal("500ms absolute deadline missed")
    }
    c.clear()
    if c.remaining(start.Add(time.Second))!=-1{t.Fatal("OS event not cleared")}
    c.push(start.Add(time.Second))
    if c.remaining(start.Add(1200*time.Millisecond))!=0{
        t.Fatal("new path epoch not independent")
    }
}

func TestPLAN028RawRtnetlinkOnlyLinkAddrRouteEvents(t *testing.T){
    packet:=func(typ uint16)[]byte{
        b:=make([]byte,16)
        binary.NativeEndian.PutUint32(b[:4],16)
        binary.NativeEndian.PutUint16(b[4:6],typ)
        return b
    }
    for _,typ:=range []uint16{
        unix.RTM_NEWROUTE,unix.RTM_DELROUTE,
        unix.RTM_NEWADDR,unix.RTM_DELADDR,
        unix.RTM_NEWLINK,unix.RTM_DELLINK,
    }{
        if !routeRelevantNetlink(packet(typ)){t.Fatalf("physical rtnetlink type %d ignored",typ)}
    }
    if routeRelevantNetlink(packet(unix.NLMSG_DONE))||routeRelevantNetlink([]byte{1,2}){
        t.Fatal("unrelated/invalid netlink packet signaled a path switch")
    }
}
