//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "context"
    "encoding/json"
    "errors"
    "fmt"
    "log"
    "net"
    "net/netip"
    "os/exec"
    "syscall"
    "time"

    "golang.org/x/sys/unix"
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

type originalLinuxCoalescer struct{
    first time.Time
    last time.Time
}
func (c *originalLinuxCoalescer) push(at time.Time){
    if c.first.IsZero(){c.first=at}
    c.last=at
}
func (c *originalLinuxCoalescer) remaining(at time.Time)time.Duration{
    if c.first.IsZero(){return -1}
    // 200ms since last notification, but at most 500ms from the first.
    quiet:=c.last.Add(200*time.Millisecond).Sub(at)
    deadline:=c.first.Add(500*time.Millisecond).Sub(at)
    if deadline<quiet{quiet=deadline}
    if quiet<0{return 0}
    return quiet
}
func (c *originalLinuxCoalescer) clear(){
    *c=originalLinuxCoalescer{}
}

func routeRelevantNetlink(datagram []byte)bool{
    msgs,err:=syscall.ParseNetlinkMessage(datagram)
    if err!=nil{return false}
    for _,m:=range msgs{
        switch m.Header.Type{
        case unix.RTM_NEWLINK,unix.RTM_DELLINK,
            unix.RTM_NEWADDR,unix.RTM_DELADDR,
            unix.RTM_NEWROUTE,unix.RTM_DELROUTE:
            return true
        }
    }
    return false
}

// True rtnetlink subscriptions, not polling link state at a periodic rate.
// The only recurring poll timeout lets context cancellation join within
// 250ms, and does not send a handshake, ping, or periodic path probe.
func watchOriginalLinuxUnderlay(
    ctx context.Context,peer netip.Addr,tunName string,
    initial originalLinuxUnderlay,
)(<-chan originalLinuxUnderlay,error){
    const groups=uint32(0x1|0x10|0x40) // RTMGRP_LINK|IPV4_IFADDR|IPV4_ROUTE
    fd,err:=unix.Socket(unix.AF_NETLINK,unix.SOCK_RAW|unix.SOCK_CLOEXEC|unix.SOCK_NONBLOCK,unix.NETLINK_ROUTE)
    if err!=nil{return nil,fmt.Errorf("native rtnetlink socket: %w",err)}
    if err=unix.Bind(fd,&unix.SockaddrNetlink{Family:unix.AF_NETLINK,Groups:groups});err!=nil{
        _=unix.Close(fd)
        return nil,fmt.Errorf("native rtnetlink subscribe: %w",err)
    }
    events:=make(chan originalLinuxUnderlay,1)
    go func(){
        defer close(events)
        defer unix.Close(fd)
        current:=initial
        var pending originalLinuxCoalescer
        var raw [8192]byte
        poll:=[]unix.PollFd{{Fd:int32(fd),Events:unix.POLLIN}}
        for ctx.Err()==nil{
            wait:=250*time.Millisecond
            if remaining:=pending.remaining(time.Now());remaining>=0&&remaining<wait{
                wait=remaining
            }
            n,pollErr:=unix.Poll(poll,int(wait/time.Millisecond))
            if errors.Is(pollErr,unix.EINTR){continue}
            if pollErr!=nil{
                log.Printf("V4_PUBLIC_PATH_NOTIFICATION_ERROR stage=poll")
                return
            }
            if n>0&&(poll[0].Revents&unix.POLLIN)!=0{
                // A burst cannot prevent the 500ms absolute deadline from
                // being checked. Read at most 256 datagrams per turn.
                for i:=0;i<256;i++{
                    bytes,_,e:=unix.Recvfrom(fd,raw[:],unix.MSG_DONTWAIT)
                    if errors.Is(e,unix.EAGAIN){break}
                    if errors.Is(e,unix.EINTR){continue}
                    if errors.Is(e,unix.ENOBUFS){
                        pending.push(time.Now()) // kernel signaled lost notifications; resample
                        break
                    }
                    if e!=nil{return}
                    if bytes==0{break}
                    if routeRelevantNetlink(raw[:bytes]){
                        pending.push(time.Now())
                    }
                }
            }
            if (poll[0].Revents&(unix.POLLERR|unix.POLLHUP))!=0{
                log.Printf("V4_PUBLIC_PATH_NOTIFICATION_ERROR stage=kernel_subscription")
                return
            }
            if pending.remaining(time.Now())!=0{continue}
            pending.clear()
            next,err:=readOriginalLinuxUnderlay(peer,tunName)
            if err!=nil{
                // No usable physical path: retain the old authenticated
                // Rust generation if still healthy; another actual OS
                // event will wake the original cold path selector.
                log.Printf("V4_PUBLIC_PATH_UNAVAILABLE role=client source=rtnetlink_os_readback")
                continue
            }
            if !next.valid()||next==current{continue}
            current=next
            // At most one latest intent: a rapid A→B→A burst is collapsed
            // to the final OS readback without unbounded goroutines/queues.
            select{case events<-next:default:
                select{case <-events:default:}
                select{case events<-next:default:}
            }
            log.Printf("V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=rtnetlink_os_readback interface=%s ifindex=%d mtu=%d coalesce_quiet_ms=200 max_ms=500",
                next.iface,next.ifindex,next.mtu)
        }
    }()
    return events,nil
}
