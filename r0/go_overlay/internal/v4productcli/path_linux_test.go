//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "encoding/binary"
    "encoding/hex"
    "os"
    "path/filepath"
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

func TestPLAN028NativeLinuxRtnetlink200Quiet500HardPhysicalFilter(t *testing.T){
    start:=time.Unix(1000,0);var c originalLinuxCoalescer
    if c.remaining(start)!=-1{t.Fatal("not armed")}
    c.push(start)
    if c.remaining(start)!=200*time.Millisecond{t.Fatal("200ms quiet")}
    c.push(start.Add(190*time.Millisecond))
    if c.remaining(start.Add(200*time.Millisecond))!=190*time.Millisecond{t.Fatal("no coalescing")}
    for ms:=210;ms<=490;ms+=20{c.push(start.Add(time.Duration(ms)*time.Millisecond))}
    if c.remaining(start.Add(495*time.Millisecond))!=5*time.Millisecond||c.remaining(start.Add(500*time.Millisecond))!=0{t.Fatal("no hard 500ms bound")}
    c.clear();if c.remaining(start.Add(time.Second))!=-1{t.Fatal("stale event")}
    original:=originalLinuxUnderlay{
        iface:"eth0",ifindex:11,src:netip.MustParseAddr("192.0.2.2"),
        gateway:netip.MustParseAddr("192.0.2.1"),mtu:1500,
    }
    other:=original;other.mtu=1280
    if !original.samePhysicalInterfaceIPv4(other){t.Fatal("MTU-only change must not reauthenticate")}
    other=original;other.gateway=netip.MustParseAddr("192.0.2.3")
    if !original.samePhysicalInterfaceIPv4(other){t.Fatal("gateway-only change must not reauthenticate")}
    other=original;other.ifindex=12
    if original.samePhysicalInterfaceIPv4(other){t.Fatal("NIC switch not detected")}
    other=original;other.src=netip.MustParseAddr("192.0.2.4")
    if original.samePhysicalInterfaceIPv4(other){t.Fatal("IPv4 change not detected")}
    other=original;other.iface="eth1"
    if original.samePhysicalInterfaceIPv4(other){t.Fatal("interface rename not detected")}
}
func TestPLAN028NativeLinuxRtnetlinkOnlyLinkAddrRoute(t *testing.T){
    packet:=func(kind uint16)[]byte{
        b:=make([]byte,16)
        binary.NativeEndian.PutUint32(b[:4],16)
        binary.NativeEndian.PutUint16(b[4:6],kind)
        return b
    }
    for _,kind:=range []uint16{unix.RTM_NEWLINK,unix.RTM_DELLINK,unix.RTM_NEWADDR,unix.RTM_DELADDR,unix.RTM_NEWROUTE,unix.RTM_DELROUTE}{
        if !routeRelevantNetlink(packet(kind)){t.Fatalf("native RTNL %d ignored",kind)}
    }
    if routeRelevantNetlink(packet(unix.NLMSG_NOOP)){t.Fatal("irrelevant netlink event")}
}

// A whole cold Game group, not an individual lane, rotates its source-port
// range on physical NIC/IP changes. All 4 distinct original FakeTCP flows
// STILL target the same server 443. Old and fresh ranges never overlap.
func TestPLAN028Game4RtnetlinkColdGenerationPortAndSingleServer443(t *testing.T){
 base:=uint16(41031)
 prior:=map[uint16]bool{}
 for seq:=uint64(1);seq<=4;seq++{
  port,err:=originalGenerationGamePort(base,seq,4)
  if err!=nil{t.Fatal(err)}
  for lane:=0;lane<4;lane++{
   src:=uint16(int(port)+lane)
   if prior[src]{
    t.Fatalf("Game4 generation %d reuses an old live source port %d",seq,src)
   }
   prior[src]=true
  }
  if seq==1&&port!=base{t.Fatal("initial Game4 source port changed")}
 }
 if _,err:=originalGenerationGamePort(65534,1,4);err==nil{
  t.Fatal("Game4 source port overflow must be rejected before SYN")
 }
 if _,err:=originalGenerationGamePort(41031,1,3);err==nil{
  t.Fatal("unsupported Game lane count admitted")
 }
}

func TestPLAN028OfflineServerRouteKeyFileCreateExclusiveNoNetwork(t *testing.T){
    dest:=filepath.Join(t.TempDir(),"server-route-key.hex")
    if e:=initServerRouteKeyFile(dest);e!=nil{t.Fatal(e)}
    st,e:=os.Lstat(dest);if e!=nil{t.Fatal(e)}
    if !st.Mode().IsRegular()||st.Mode().Perm()!=0600{t.Fatal("route-key must be owner-only regular file")}
    data,e:=os.ReadFile(dest);if e!=nil{t.Fatal(e)}
    key,e:=hex.DecodeString(string(data[:len(data)-1]))
    if e!=nil||len(key)!=32||data[len(data)-1]!='\n'{t.Fatal("server did not generate 32B random key")}
    if e=initServerRouteKeyFile(dest);e==nil{t.Fatal("offline server route-key silently overwritten")}
    link:=filepath.Join(t.TempDir(),"link")
    if e=os.Symlink(dest,link);e!=nil{t.Fatal(e)}
    if e=initServerRouteKeyFile(link);e==nil{t.Fatal("symlink accepted as private route-key target")}
}
