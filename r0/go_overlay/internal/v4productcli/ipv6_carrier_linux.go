//go:build (linux || android) && (amd64 || arm64) && cgo && wbd_v4_embedded_go

package v4productcli

import (
 "context"
 "fmt"
 "net/netip"
 "os"
 "os/exec"
 "strings"
 "time"

 "github.com/lly8666/wobuzhidao/internal/v4productcli/rootjournal"
)

const androidIPv6CarrierJournal="/data/local/tmp/wbd-next-root/ipv6-carrier-journal.json"
const serverIPv6CarrierJournal="/run/wbd-next-ipv6/ipv6-carrier-journal.json"

func originalIPv6Command(tool string)rootjournal.Runner{
 return func(args ...string)(string,error){
  ctx,cancel:=context.WithTimeout(context.Background(),5*time.Second);defer cancel()
  b,e:=exec.CommandContext(ctx,tool,args...).CombinedOutput()
  if e!=nil||len(b)>256<<10{return "",fmt.Errorf("IPv6 carrier %s %q failed: %w",tool,args,e)}
  return string(b),nil
 }
}
func originalIPv6Batch(rows [][]string)error{
 for from:=0;from<len(rows);{
  family:=rows[from][0]
  if family!="-4"&&family!="-6"{return fmt.Errorf("invalid IPv6 carrier FIB family")}
  var input strings.Builder
  to:=from
  for to<len(rows)&&rows[to][0]==family{
   input.WriteString(strings.Join(rows[to][1:]," "));input.WriteByte('\n');to++
  }
  ctx,cancel:=context.WithTimeout(context.Background(),8*time.Second)
  command:=exec.CommandContext(ctx,"ip",family,"-batch","-")
  command.Stdin=strings.NewReader(input.String())
  b,e:=command.CombinedOutput();cancel()
  if e!=nil||len(b)>256<<10{return fmt.Errorf("IPv6 carrier FIB batch failed: %v",e)}
  from=to
 }
 return nil
}
func originalIPv6CarrierMTU(tun *ownedTun)(int,error){
 mtu,e:=readOwnedTunMTU(tun.name);if e!=nil{return 0,e}
 mtu-=20 // exact IPv4 encapsulation header, not outer FakeTCP overhead
 if mtu<1280{mtu=1280} // IPv6 minimum; nopmtudisc allows IPv4 fragmentation
 if mtu>1480{mtu=1480}
 return mtu,nil
}
func startOriginalServerIPv6Carrier(c config,tun *ownedTun)(*rootjournal.IPv6Owner,error){
 ip,fw4,fw6:=originalIPv6Command("ip"),originalIPv6Command("iptables"),originalIPv6Command("ip6tables")
 if e:=rootjournal.RecoverIPv6CarrierBatch(ip,fw4,fw6,originalIPv6Batch,serverIPv6CarrierJournal);e!=nil{return nil,e}
 forward,e:=os.ReadFile("/proc/sys/net/ipv6/conf/all/forwarding")
 if e!=nil||strings.TrimSpace(string(forward))!="1"{return nil,fmt.Errorf("enable server IPv6 forwarding before --inner-ipv6")}
 // No host-global forwarding/sysctl or default route mutation.
 route,e:=ip("-6","route","get","2606:4700:4700::1111","oif",c.rawInterface)
 if e!=nil||!rootjournal.SelectedUIDRouteGetUsesTun(route,c.rawInterface){
  return nil,fmt.Errorf("server IPv6 egress route unavailable on selected physical interface")
 }
 local,e:=netip.ParsePrefix(tun.cidr);if e!=nil{return nil,e}
 mtu,e:=originalIPv6CarrierMTU(tun);if e!=nil{return nil,e}
 owner,e:=rootjournal.NewIPv6CarrierBatch(ip,fw4,fw6,originalIPv6Batch,serverIPv6CarrierJournal,
  rootjournal.IPv6Plan{Server:true,Tun:tun.name,Local4:local.Addr().String(),Gateway4:local.Addr().String(),Egress:c.rawInterface,MTU:mtu})
 if e!=nil{return nil,e}
 fmt.Fprintf(os.Stderr,"V4_PUBLIC_SERVER_IPV6_CARRIER_READY gateway4=%s gateway6=%s mtu=%d kernel_sit_6rd=1\n",
  local.Addr(),rootjournal.IPv6LeaseAddress(local.Addr()),mtu)
 return owner,nil
}
