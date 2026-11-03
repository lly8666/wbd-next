//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net"
    "net/netip"
    "os/exec"
    "time"
)

// PLAN028 cold network authority. These are physical ROUTE readbacks, never
// settings copied from a GUI or from the VPN's own TUN device. Only the
// concrete numeric remote endpoint is resolved here; DNS remains PLAN029.
type originalLinuxUnderlay struct{
    iface string
    ifindex uint32
    src netip.Addr
    gateway netip.Addr
    peer netip.Addr
    mtu int
}
func (p originalLinuxUnderlay) valid()bool{
    return p.iface!=""&&p.ifindex>0&&p.src.Is4()&&p.peer.Is4()&&
       p.mtu>=576&&p.mtu<=65535
}

type originalRouteJSON struct{
    Dst string `json:"dst"`
    Dev string `json:"dev"`
    Prefsrc string `json:"prefsrc"`
    Src string `json:"src"`
    Gateway string `json:"gateway"`
    Type string `json:"type"`
    MTU int `json:"mtu"` // ip -j route get may expose a per-destination ceiling
}
func parseOriginalRouteJSON(raw []byte,peer netip.Addr,tunName string,
    getInterface func(string)(*net.Interface,error),
)(originalLinuxUnderlay,error){
    var p originalLinuxUnderlay
    if !peer.Is4()||getInterface==nil{return p,fmt.Errorf("original physical route needs numeric IPv4 endpoint")}
    var routes []originalRouteJSON
    if err:=json.Unmarshal(raw,&routes);err!=nil{return p,err}
    if len(routes)!=1||routes[0].Dev==""||routes[0].Dev==tunName||
       routes[0].Type=="local"||routes[0].Type=="blackhole"||
       routes[0].Type=="unreachable"||routes[0].Type=="prohibit"{
        return p,fmt.Errorf("no unique physical route for protected TLS peer")
    }
    r:=routes[0]
    srcText:=r.Prefsrc
    if srcText==""{srcText=r.Src}
    src,err:=netip.ParseAddr(srcText)
    if err!=nil||!src.Is4()||src.IsUnspecified()||src.IsMulticast(){
        return p,fmt.Errorf("physical route has no usable selected IPv4 source")
    }
    iface,err:=getInterface(r.Dev)
    if err!=nil||iface==nil||iface.Index<1||iface.MTU<576{
        return p,fmt.Errorf("physical route interface unavailable")
    }
    var gateway netip.Addr
    if r.Gateway!=""{
        gateway,err=netip.ParseAddr(r.Gateway)
        if err!=nil||!gateway.Is4(){return p,fmt.Errorf("physical gateway is not IPv4")}
    }
    // A destination route may enforce a smaller MTU than the interface.
    // Ignore neither the actual kernel route metric nor the interface cap:
    // using only iface.MTU would admit oversized M1 records after a route
    // change and silently create an inner-TCP black hole.
    effectiveMTU:=iface.MTU
    if r.MTU!=0{
        if r.MTU<576||r.MTU>65535{
            return p,fmt.Errorf("invalid physical route MTU %d",r.MTU)
        }
        if r.MTU<effectiveMTU{effectiveMTU=r.MTU}
    }
    p=originalLinuxUnderlay{
        iface:iface.Name,ifindex:uint32(iface.Index),src:src,
        gateway:gateway,peer:peer,mtu:effectiveMTU,
    }
    return p,nil
}

// Route-get observes the EFFECTIVE Linux kernel decision to reach the server,
// not RTM_NEWROUTE by itself. TUN-created routes must never trigger an
// underlay-to-TUN recursion or a TLS reconnect storm.
func readOriginalLinuxUnderlay(peer netip.Addr,tunName string)(originalLinuxUnderlay,error){
    var zero originalLinuxUnderlay
    if !peer.Is4(){return zero,fmt.Errorf("only numeric original IPv4 endpoint is supported")}
    ctx,cancel:=context.WithTimeout(context.Background(),2*time.Second)
    defer cancel()
    data,err:=exec.CommandContext(ctx,"ip","-j","-4","route","get",peer.String()).Output()
    if err!=nil{return zero,fmt.Errorf("original Linux physical route: %w",err)}
    p,err:=parseOriginalRouteJSON(data,peer,tunName,net.InterfaceByName)
    if err!=nil{return zero,err}
    // A route's cached preferred source must still be assigned to the
    // effective interface. Prevent stale local-IP reuse after address loss.
    iface,err:=net.InterfaceByIndex(int(p.ifindex))
    if err!=nil{return zero,err}
    addrs,err:=iface.Addrs()
    if err!=nil{return zero,err}
    for _,a:=range addrs{
        ipnet,ok:=a.(*net.IPNet)
        if !ok{continue}
        addr,ok:=netip.AddrFromSlice(ipnet.IP)
        if ok&&addr.Unmap()==p.src{return p,nil}
    }
    return zero,fmt.Errorf("physical route source not installed on selected interface")
}

// Only the default physical egress interface and selected IPv4 may trigger
// a new native generation. Route metric/MTU still constrain new TLS budget.
const originalPhysicalCheckInterval=2*time.Second
func (p originalLinuxUnderlay) samePhysicalInterfaceIPv4(next originalLinuxUnderlay)bool{
    return p.ifindex==next.ifindex&&p.iface==next.iface&&p.src==next.src
}

// One 2-second cold physical readback, no netlink route/addr subscriptions.
func watchOriginalLinuxUnderlay(
    ctx context.Context,peer netip.Addr,tunName string,
    initial originalLinuxUnderlay,
)(<-chan originalLinuxUnderlay,error){
    if !initial.valid(){return nil,fmt.Errorf("initial physical path invalid")}
    events:=make(chan originalLinuxUnderlay,1)
    go func(){
        defer close(events)
        ticker:=time.NewTicker(originalPhysicalCheckInterval)
        defer ticker.Stop()
        current:=initial
        for{
            select{
            case <-ctx.Done():return
            case <-ticker.C:
                next,err:=readOriginalLinuxUnderlay(peer,tunName)
                if err!=nil||!next.valid(){continue}
                same:=current.samePhysicalInterfaceIPv4(next)
                current=next
                if same{continue}
                select{case events<-next:default:
                    select{case <-events:default:}
                    select{case events<-next:default:}
                }
                log.Printf("V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=physical_if_ipv4_2s_poll interface=%s ifindex=%d src=%s mtu=%d",
                    next.iface,next.ifindex,next.src,next.mtu)
            }
        }
    }()
    return events,nil
}
