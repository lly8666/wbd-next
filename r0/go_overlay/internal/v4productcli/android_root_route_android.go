//go:build android && (arm64 || amd64) && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "fmt"
    "bytes"
    "crypto/rand"
    "sort"
    "context"
    "errors"
    "syscall"
    "time"
    "net"
    "net/netip"
    "os"
    "os/exec"
    "strconv"
    "strings"

    "github.com/lly8666/wobuzhidao/internal/v4productcli/rootjournal"
    "github.com/lly8666/wobuzhidao/internal/v4productcli/dnsnative"
)

// Read-only route-get for each selected App UID; never changes kernel state.
// Mismatch is a diagnostic, not an authorization or a route mutation.
func originalAndroidSelectedUIDRouteGet(runner rootjournal.Runner,uids []int,tun string){
 for _,uid:=range uids{
  out,err:=runner("-4","route","get","1.1.1.1","uid",strconv.Itoa(uid))
  if err!=nil{
   fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class=UNAVAILABLE")
   return
  }
  if !rootjournal.SelectedUIDRouteGetUsesTun(out,tun){
   fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class=MISMATCH")
   return
  }
 }
 fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class=MATCHED_TUN")
}

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
            return nil,fmt.Errorf("Android group route must contain 2..16 distinct sorted ordinary App UIDs")
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
    if e:=rootjournal.RecoverIPv6CarrierBatch(runner,androidDNSFirewall,androidDNSFirewall6,originalIPv6Batch,androidIPv6CarrierJournal);e!=nil{return nil,e}
    if e:=rootjournal.RecoverTether(runner,androidDNSFirewall,androidTetherJournal);e!=nil{return nil,e}
    if e:=rootjournal.RecoverSystemDNS6(runner,androidDNSFirewall6,androidDNSIPBatch,nil,androidSystemDNS6Journal);e!=nil{return nil,e}
    if e:=rootjournal.RecoverSystemDNS(runner,androidDNSFirewall,androidDNSIPBatch,androidDNSBatch,androidSystemDNSJournal);e!=nil{return nil,e}
    if e:=rootjournal.RecoverDNS(runner,androidDNSFirewall,androidDNSBatch,androidDNSJournal);e!=nil{return nil,e}
    if c.androidRouteAllApps{
        full,e:=rootjournal.NewAllApps(runner,rootOnlyJournal,rootjournal.AllAppPlan{
            ExcludedAppIDs:append([]int(nil),c.androidRouteExcludeAppIDs...),
            Tun:tun.name,Lease:lease.String(),ServerIP:c.peerIP.String(),
            DirectCIDRs:append([]string(nil),c.androidDirectCIDRs...),
            Underlay:c.rawInterface,
            NetworkHandle:c.androidNetworkHandle,IfIndex:physical.Index,
        })
        if e!=nil{return nil,e}
        stop,e:=startAndroidAppTCPDNS(c,tun,lease,runner,full.Stop)
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
        return stop,nil
    }
    if len(c.androidRouteUIDs)>0{
        group,e:=rootjournal.NewGroup(runner,rootOnlyJournal,rootjournal.GroupPlan{
            UIDs:append([]int(nil),c.androidRouteUIDs...),
            Tun:tun.name,Lease:lease.String(),ServerIP:c.peerIP.String(),
            DirectCIDRs:append([]string(nil),c.androidDirectCIDRs...),
            Underlay:c.rawInterface,NetworkHandle:c.androidNetworkHandle,IfIndex:physical.Index,
        })
        if e!=nil{return nil,e}
        stop,e:=startAndroidAppTCPDNS(c,tun,lease,runner,group.Stop)
        if e!=nil{return nil,e}
        originalAndroidSelectedUIDRouteGet(runner,c.androidRouteUIDs,tun.name)
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
        return stop,nil
    }
    session,e:=rootjournal.New(runner,rootOnlyJournal,rootjournal.Plan{
        UID:c.androidRouteUID,Tun:tun.name,Lease:lease.String(),
        ServerIP:c.peerIP.String(),DirectCIDRs:append([]string(nil),c.androidDirectCIDRs...),
        Underlay:c.rawInterface,NetworkHandle:c.androidNetworkHandle,
        IfIndex:physical.Index,
    })
    if e!=nil{return nil,e}
    stop,e:=startAndroidAppTCPDNS(c,tun,lease,runner,session.Stop)
    if e!=nil{return nil,e}
    originalAndroidSelectedUIDRouteGet(runner,[]int{c.androidRouteUID},tun.name)
    // This exact root-only rule is the sole route grant. The kernel
    // readback and fsync'd journal are complete before a positive log.
    fmt.Fprintf(os.Stderr,
        "V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED uid=%d table=%d priority=%d lease=%s physical_ifindex=%d network_handle=%s\n",
        c.androidRouteUID,rootjournal.Table,rootjournal.Priority,
        lease,physical.Index,strconv.FormatUint(c.androidNetworkHandle,10))
    return stop,nil
}
const androidDNSJournal="/data/local/tmp/wbd-next-root/dns-tcp-journal.json"
const androidSystemDNSJournal="/data/local/tmp/wbd-next-root/system-dns-journal.json"
const androidSystemDNS6Journal="/data/local/tmp/wbd-next-root/system-dns6-journal.json"
// iproute2 batch is cold-only. On a partial failure exact journal state
// is read back and withdrawn; never replay a partially executed batch.
func androidDNSIPBatch(rows [][]string)error{
 if len(rows)==0{return nil}
 family:=rows[0][0]
 if family!="-4"&&family!="-6"{return fmt.Errorf("invalid system DNS route family")}
 var input strings.Builder
 for _,row:=range rows{
  if len(row)<2||row[0]!=family{return fmt.Errorf("mixed system DNS route family")}
  input.WriteString(strings.Join(row[1:]," "));input.WriteByte('\n')
 }
 ctx,cancel:=context.WithTimeout(context.Background(),8*time.Second);defer cancel()
 command:=exec.CommandContext(ctx,"ip",family,"-batch","-")
 command.Stdin=strings.NewReader(input.String())
 if _,e:=command.CombinedOutput();e!=nil{return fmt.Errorf("system DNS UID route batch: %w",e)}
 return nil
}
func androidDNSFirewall(args ...string)(string,error){
 ctx,cancel:=context.WithTimeout(context.Background(),3*time.Second);defer cancel()
 b,e:=exec.CommandContext(ctx,"iptables",args...).CombinedOutput()
 if e!=nil{return "",fmt.Errorf("owned TCP DNS NAT: %w",e)}
 return string(b),nil
}
func androidDNSFirewall6(args ...string)(string,error){
 ctx,cancel:=context.WithTimeout(context.Background(),3*time.Second);defer cancel()
 b,e:=exec.CommandContext(ctx,"ip6tables",args...).CombinedOutput()
 if e!=nil{return "",fmt.Errorf("owned IPv6 DNS NAT: %w",e)}
 return string(b),nil
}
func androidDNSBatch(rows [][]string)error{
 // Batch all exact UID ranges in one cold kernel transaction where
 // Android exposes iptables-restore; otherwise use the same exact rules.
 restore,e:=exec.LookPath("iptables-restore")
 if e!=nil{
  for _,row:=range rows{
   if _,e=androidDNSFirewall(append([]string{"-w","2","-t","nat"},row...)...);e!=nil{return e}
  }
  return nil
 }
 var input strings.Builder;input.WriteString("*nat\n")
 for _,row:=range rows{input.WriteString(strings.Join(row," "));input.WriteByte('\n')}
 input.WriteString("COMMIT\n")
 ctx,cancel:=context.WithTimeout(context.Background(),5*time.Second);defer cancel()
 command:=exec.CommandContext(ctx,restore,"-w","2","--noflush")
 command.Stdin=strings.NewReader(input.String())
 if _,e=command.CombinedOutput();e!=nil{return fmt.Errorf("owned TCP DNS batch: %w",e)}
 return nil
}
func startAndroidAppTCPDNS(c config,tun *ownedTun,lease netip.Prefix,
 runner rootjournal.Runner,stopUID func()error)(func()error,error){
 tetherDNS:=c.androidTetherInterface!=""&&(c.androidTunnelDNS||c.androidPhysicalDNS||c.androidCNDNSSplit)
 finish:=func(stop func()error,relay *dnsnative.AppTCPDNS)(func()error,error){
  next,e:=startAndroidTether(c,tun,lease,runner,stop,relay)
  if e!=nil{return nil,e}
  return startOriginalAndroidIPv6Carrier(c,tun,lease,runner,next,relay)
 }
 if !c.androidAppTCPDNS&&!tetherDNS{return finish(stopUID,nil)}
 tunnel:=c.androidTunnelDNS||c.androidCNDNSSplit
 physicalEndpoint:=net.JoinHostPort(c.androidPhysicalDNSUpstream.String(),"53")
 tunnelIP:=c.androidTunnelDNSUpstream
 if !tunnelIP.IsValid(){tunnelIP=netip.MustParseAddr("1.1.1.1")}
 tunnelEndpoint:=net.JoinHostPort(tunnelIP.String(),"53")
 dial:=func(ctx context.Context,path dnsnative.Path,network,endpoint string)(net.Conn,error){
  if network!="tcp"&&!((c.androidSystemDNS||tetherDNS)&&network=="udp"){return nil,dnsnative.ErrUnbound}
  if path==dnsnative.Physical{
   return c.androidPhysicalDNSDial(ctx,path,network,endpoint)
  }
  if !tunnel||path!=dnsnative.Tunnel||endpoint!=tunnelEndpoint{return nil,dnsnative.ErrUnbound}
  // Exact original authenticated lease, TUN interface and a separate
  // root-only source/destination rule to the fixed 1.1.1.1/32. This is
  // ordinary TCP entering the existing Rust M4, not a second TUN reader.
  var local net.Addr=&net.TCPAddr{IP:net.IP(lease.Addr().AsSlice())}
  if network=="udp"{local=&net.UDPAddr{IP:net.IP(lease.Addr().AsSlice())}}
  d:=net.Dialer{LocalAddr:local}
  d.ControlContext=func(ctx context.Context,network,address string,raw syscall.RawConn)error{
   var bindErr error
   e:=raw.Control(func(fd uintptr){
    bindErr=syscall.SetsockoptString(int(fd),syscall.SOL_SOCKET,syscall.SO_BINDTODEVICE,tun.name)
   })
   return errors.Join(e,bindErr)
  }
  return d.DialContext(ctx,network+"4",endpoint)
 }
 var match dnsnative.CNMatch
 if c.androidCNDNSSplit{match=c.androidCNSnapshot.Match}
 relay,e:=dnsnative.StartAppTCPDNS(dial,match,c.androidCNDNSSplit,c.androidPhysicalDNS,physicalEndpoint,tunnelEndpoint)
 if e!=nil{return nil,errors.Join(e,stopUID())}
 uids:=append([]int(nil),c.androidRouteUIDs...)
 if c.androidRouteUID!=0{uids=[]int{c.androidRouteUID}}
 plan:=rootjournal.DNSPlan{Tun:tun.name,Lease:lease.String(),Port:relay.Port(),Tunnel:tunnel,TunnelUpstream:tunnelIP.String(),
   All:c.androidRouteAllApps,UIDs:uids,ExcludedAppIDs:c.androidRouteExcludeAppIDs,NoAppNAT:!c.androidAppTCPDNS}
 if c.androidSystemDNS{
  if e=relay.EnableUDP();e!=nil{return nil,errors.Join(e,relay.Close(),stopUID())}
 }
 owner,e:=rootjournal.NewDNS(runner,androidDNSFirewall,androidDNSBatch,androidDNSJournal,plan)
 if e!=nil{return nil,errors.Join(e,relay.Close(),stopUID())}
 var systemOwner,systemOwner6 *rootjournal.SystemDNSOwner
 if c.androidSystemDNS{
  // Android Network.getNetworkHandle stores netId in its high 32 bits.
  // No root/system wildcard rule and no modification of netd configuration.
  systemOwner,e=rootjournal.NewSystemDNS(runner,androidDNSFirewall,androidDNSIPBatch,androidDNSBatch,
   androidSystemDNSJournal,rootjournal.SystemDNSPlan{DNSPlan:plan,NetID:uint32(c.androidNetworkHandle>>32)})
  if e!=nil{return nil,errors.Join(e,owner.Stop(),relay.Close(),stopUID())}
  fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_SYSTEM_DNS_IPV4_READY role=client uid_netid_port53=1")
 }
 if c.androidSystemDNS6{
  port,err:=relay.EnableIPv6()
  if err!=nil{return nil,errors.Join(err,systemOwner.Stop(),owner.Stop(),relay.Close(),stopUID())}
  plan6:=plan;plan6.Port=port
  systemOwner6,e=rootjournal.NewSystemDNS(runner,androidDNSFirewall6,androidDNSIPBatch,nil,
   androidSystemDNS6Journal,rootjournal.SystemDNSPlan{DNSPlan:plan6,NetID:uint32(c.androidNetworkHandle>>32),IPv6:true})
  if e!=nil{return nil,errors.Join(e,systemOwner.Stop(),owner.Stop(),relay.Close(),stopUID())}
  fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_SYSTEM_DNS_IPV6_READY role=client uid_netid_port53=1 ipv4_upstream=1")
 }
 if c.androidAppTCPDNS{fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_APP_TCP_DNS_READY role=client kernel_tcp=1 exact_uid_nat=1")}
 stopDNS:=func()error{
  // Withdraw capture first; join DNS streams before the original M4 Stop.
  var systemErr,error6 error
  if systemOwner6!=nil{error6=systemOwner6.Stop()}
  if systemOwner!=nil{systemErr=systemOwner.Stop()}
  return errors.Join(error6,systemErr,errors.Join(owner.Stop(),relay.Close(),stopUID()))
 }
 return finish(stopDNS,relay)
}


const androidTetherJournal="/data/local/tmp/wbd-next-root/tether-journal.json"
func startAndroidTether(c config,tun *ownedTun,lease netip.Prefix,runner rootjournal.Runner,stop func()error,relay *dnsnative.AppTCPDNS)(func()error,error){
 if c.androidTetherInterface==""{return stop,nil}
 fail:=func(e error)(func()error,error){return nil,errors.Join(e,stop())}
 d,e:=net.InterfaceByName(c.androidTetherInterface)
 if e!=nil||d==nil||d.Index!=c.androidTetherIfindex||d.Flags&net.FlagUp==0||d.Name==c.rawInterface||d.Name==tun.name{
  return fail(fmt.Errorf("tether downstream changed"))
 }
 prefix,e:=netip.ParsePrefix(c.androidTetherSubnet)
 if e!=nil{return fail(e)}
 addrs,e:=d.Addrs();if e!=nil{return fail(e)}
 var gateway netip.Addr
 for _,a:=range addrs{
  p,e:=netip.ParsePrefix(a.String())
  if e==nil&&p.Masked()==prefix{
   if gateway.IsValid(){return fail(fmt.Errorf("ambiguous tether gateway"))}
   gateway=p.Addr()
  }
 }
 if !gateway.IsValid()||prefix.Contains(c.localIP)||prefix.Contains(c.peerIP){return fail(fmt.Errorf("tether subnet changed or overlaps carrier"))}
 forward,e:=os.ReadFile("/proc/sys/net/ipv4/ip_forward")
 if e!=nil||strings.TrimSpace(string(forward))!="1"{return fail(fmt.Errorf("enable existing Android tethering first"))}
 // Do not change Android offload settings or bypass its BPF ownership.
 // Only an explicitly software-forwarded downstream is supported here.
 ctx,cancel:=context.WithTimeout(context.Background(),5*time.Second);defer cancel()
 offload,e:=exec.CommandContext(ctx,"settings","get","global","tether_offload_disabled").Output()
 if e!=nil||strings.TrimSpace(string(offload))!="1"{return fail(fmt.Errorf("software tether requires hardware offload disabled"))}
 dump,e:=exec.CommandContext(ctx,"dumpsys","tethering").Output()
 if e!=nil||!strings.Contains(string(dump),"mIsBpfEnabled: false"){return fail(fmt.Errorf("software tether requires verified inactive BPF offload"))}
 plan:=rootjournal.TetherPlan{Tun:tun.name,Downstream:d.Name,Subnet:prefix.String(),Lease:lease.String()}
 if relay!=nil{
  port,err:=relay.EnableDownstream(gateway,prefix)
  if err!=nil{return fail(err)}
  plan.DNSAddress,plan.DNSPort=gateway.String(),port
 }
 owner,e:=rootjournal.NewTether(runner,androidDNSFirewall,androidTetherJournal,plan)
 if e!=nil{return fail(e)}
 if plan.DNSPort!=0{fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_TETHER_DNS_READY role=client udp_tcp53=1")}
 fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_TETHER_READY role=client software_ipv4=1")
 return func()error{return errors.Join(owner.Stop(),stop())},nil
}

func startOriginalAndroidIPv6Carrier(c config,tun *ownedTun,lease netip.Prefix,runner rootjournal.Runner,stop func()error,relay *dnsnative.AppTCPDNS)(func()error,error){
 if c.androidIPv6Gateway==""{return stop,nil}
 fail:=func(e error)(func()error,error){return nil,errors.Join(e,stop())}
 gateway,e:=netip.ParseAddr(c.androidIPv6Gateway)
 if e!=nil||gateway==c.peerIP||gateway==c.localIP{return fail(fmt.Errorf("IPv6 carrier gateway must be server TUN IPv4, not physical peer"))}
 mtu,e:=originalIPv6CarrierMTU(tun);if e!=nil{return fail(e)}
 uids:=append([]int(nil),c.androidRouteUIDs...)
 if c.androidRouteUID!=0{uids=[]int{c.androidRouteUID}}
 plan:=rootjournal.IPv6Plan{Tun:tun.name,Local4:lease.Addr().String(),Gateway4:gateway.String(),MTU:mtu,
   All:c.androidRouteAllApps,UIDs:uids,ExcludedAppIDs:c.androidRouteExcludeAppIDs,
   DirectCIDRs:append([]string(nil),c.androidIPv6DirectCIDRs...)}
 if c.androidIPv6DirectLAN{
  physical:=c.rawInterface
  if c.androidClatParent!=""{physical=c.androidClatParent}
  iface,e:=net.InterfaceByName(physical)
  if e!=nil{return fail(e)}
  addrs,e:=iface.Addrs()
  if e!=nil{return fail(e)}
  raw:=make([]string,0,len(addrs))
  for _,a:=range addrs{raw=append(raw,a.String())}
  plan.DirectCIDRs,e=rootjournal.IPv6DirectLAN(plan.DirectCIDRs,raw)
  if e!=nil{return fail(e)}
 }
 if c.androidTetherInterface!=""{
  prefixes,e:=originalAndroidTetherIPv6(c)
  if e!=nil{return fail(e)}
  if len(prefixes)!=0{
   plan.Downstream,plan.Downstream6=c.androidTetherInterface,prefixes
   if relay!=nil{
    for _,raw:=range prefixes{
     prefix:=netip.MustParsePrefix(raw)
     port,err:=relay.EnableDownstream6(prefix.Addr(),prefix.Masked())
     if err!=nil{return fail(err)}
     plan.DownstreamDNSPorts=append(plan.DownstreamDNSPorts,port)
    }
   }
  }
 }
 owner,e:=rootjournal.NewIPv6CarrierBatch(runner,androidDNSFirewall,androidDNSFirewall6,originalIPv6Batch,androidIPv6CarrierJournal,plan)
 if e!=nil{return fail(e)}
 local6,peer6:=rootjournal.IPv6LeaseAddress(lease.Addr()),rootjournal.IPv6LeaseAddress(gateway)
 // Local link/rule readback alone is not remote IPv6 readiness.
 // One cold kernel Echo via original authenticated M4, no new TLS or
 // permanent timer/socket. A legacy IPv4-only server cannot satisfy it.
 if e=originalAndroidIPv6PeerEcho(local6,peer6);e!=nil{return fail(errors.Join(e,owner.Stop()))}
 fmt.Fprintf(os.Stderr,"V4_PUBLIC_ANDROID_IPV6_CARRIER_PEER_ECHO_READY role=client lease6=%s mtu=%d kernel_sit=1\n",local6,mtu)
 if len(plan.DownstreamDNSPorts)!=0{fmt.Fprintln(os.Stderr,"V4_PUBLIC_ANDROID_TETHER_IPV6_DNS_READY role=client udp_tcp53=1")}
 if len(plan.Downstream6)!=0{
  fmt.Fprintf(os.Stderr,"V4_PUBLIC_ANDROID_TETHER_IPV6_READY role=client prefixes=%d kernel_snat66=1\n",len(plan.Downstream6))
 }
 return func()error{return errors.Join(owner.Stop(),stop())},nil
}
// Read only actual addresses on the previously B65-verified software
// downstream. No router advertisement, new prefix allocation or Android
// tether configuration change. No IPv6 scope => retain IPv4-only tether.
func originalAndroidTetherIPv6(c config)([]string,error){
 nic,e:=net.InterfaceByName(c.androidTetherInterface)
 if e!=nil||nic==nil||nic.Index!=c.androidTetherIfindex||nic.Flags&net.FlagUp==0{return nil,fmt.Errorf("tether downstream changed before IPv6 grant")}
 addresses,e:=nic.Addrs();if e!=nil{return nil,e}
 byPrefix:=map[netip.Prefix]netip.Addr{}
 for _,a:=range addresses{
  p,e:=netip.ParsePrefix(a.String())
  if e!=nil||p.Bits()!=64||!p.Addr().Is6()||p.Addr().Is4In6()||!p.Addr().IsGlobalUnicast()||
   p.Addr()==p.Masked().Addr(){continue}
  if netip.MustParsePrefix(rootjournal.IPv6CarrierPrefix).Overlaps(p){return nil,fmt.Errorf("tether IPv6 prefix overlaps WBD carrier")}
  old,ok:=byPrefix[p.Masked()]
  if !ok||p.Addr().Compare(old)<0{byPrefix[p.Masked()]=p.Addr()}
 }
 if len(byPrefix)==0{return nil,nil}
 if len(byPrefix)>4{return nil,fmt.Errorf("too many active IPv6 downstream prefixes")}
 forwarding,e:=os.ReadFile("/proc/sys/net/ipv6/conf/all/forwarding")
 if e!=nil||strings.TrimSpace(string(forwarding))!="1"{return nil,fmt.Errorf("existing Android tether IPv6 forwarding not enabled")}
 var out []string
 for _,ip:=range byPrefix{out=append(out,netip.PrefixFrom(ip,64).String())}
 sort.Strings(out)
 return out,nil
}
func originalAndroidIPv6PeerEcho(local,peer netip.Addr)error{
 ctx,cancel:=context.WithTimeout(context.Background(),5*time.Second);defer cancel()
 d:=net.Dialer{LocalAddr:&net.IPAddr{IP:net.IP(local.AsSlice())}}
 d.ControlContext=func(ctx context.Context,network,address string,raw syscall.RawConn)error{
  var bindErr error
  e:=raw.Control(func(fd uintptr){bindErr=syscall.SetsockoptString(int(fd),syscall.SOL_SOCKET,syscall.SO_BINDTODEVICE,"wbd_sit0")})
  return errors.Join(e,bindErr)
 }
 conn,e:=d.DialContext(ctx,"ip6:58",peer.String())
 if e!=nil{return fmt.Errorf("IPv6 carrier peer probe socket: %w",e)}
 defer conn.Close()
 var request [24]byte
 request[0]=128 // ICMPv6 Echo Request; kernel supplies checksum
 if _,e=rand.Read(request[4:]);e!=nil{return e}
 var reply [256]byte
 for attempt:=0;attempt<2;attempt++{
  deadline:=time.Now().Add(2*time.Second)
  if end,ok:=ctx.Deadline();ok&&deadline.After(end){deadline=end}
  if e=conn.SetDeadline(deadline);e!=nil{return e}
  if _,e=conn.Write(request[:]);e!=nil{continue}
  for{
   n,e:=conn.Read(reply[:]);if e!=nil{break}
   if n==len(request)&&reply[0]==129&&reply[1]==0&&bytes.Equal(reply[4:n],request[4:]){return nil}
  }
 }
 return fmt.Errorf("IPv6 carrier peer did not answer: verify Linux --inner-ipv6 and actual server TUN IPv4")
}

