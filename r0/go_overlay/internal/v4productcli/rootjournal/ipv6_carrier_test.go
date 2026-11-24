package rootjournal

import (
 "fmt"
 "net/netip"
 "path/filepath"
 "strings"
 "testing"
)
func TestB70IPv6OwnedCarrierAndRestore(t *testing.T){testIPv6Carrier(t,false)}
func TestB71IPv6TetherAndColdPeerScope(t *testing.T){testIPv6Carrier(t,true)}
func TestB72IPv6DirectCIDRsAndLAN(t *testing.T){
 manual,e:=ParseIPv6DirectCIDRs("fd12:3456::1/48,2001:db8:1234::/64")
 if e!=nil||strings.Join(manual,",")!="fd12:3456::/48,2001:db8:1234::/64"{t.Fatal(manual,e)}
 got,e:=IPv6DirectLAN(manual,[]string{"192.168.1.2/24","2001:db8:1234::2/64","2001:db8:abcd::2/64","fe80::1/64"})
 if e!=nil||strings.Join(got,",")!="fd12:3456::/48,2001:db8:1234::/64,fe80::/10,ff00::/8,2001:db8:abcd::/64"{t.Fatal(got,e)}
 testIPv6Carrier(t,true)
}
func testIPv6Carrier(t *testing.T,tether bool){
 if got:=IPv6LeaseAddress(netip.MustParseAddr("10.219.17.2")).String();got!="fd65:5742:7636:1102::1"{t.Fatal(got)}
 for _,server:=range []bool{false,true}{
  p:=IPv6Plan{Version:1,Tun:"wbd0",Local4:"10.219.17.2",Gateway4:"10.219.0.1",MTU:1280,UIDs:[]int{11200,11201}}
  if server{p.Server=true;p.Local4=p.Gateway4;p.Egress="eth0";p.UIDs=nil}else if tether{p.Downstream="ap0";p.Downstream6=[]string{"2001:db8:1234::1/64","fd12:3456:789a::1/64"};p.DirectCIDRs=[]string{"2001:db8:1234::/64","fd12:3456::/48","fe80::/10"}}
  if !p.valid(){t.Fatal("valid carrier refused",p)}
  cmds:=p.commands();present:=make([]bool,len(cmds));var link,addr bool
  ip:=func(a ...string)(string,error){
   key:=strings.Join(a," ")
   switch key{
   case "-d -o link show":
    if link{return fmt.Sprintf("9: wbd_sit0@%s: <UP> mtu 1280 alias %s sit remote %s local %s 6rd-prefix %s 6rd-relay_prefix %s",p.Tun,ipv6CarrierMarker,p.remote4(),p.Local4,IPv6CarrierPrefix,p.relay()),nil};return "",nil
   case "-6 -o addr show":if addr{return "9: wbd_sit0 inet6 "+p.local6()+"/128 scope global nodad",nil};return "",nil
   case "link del dev wbd_sit0":link=false;addr=false;return "",nil
   }
   if strings.HasPrefix(key,"link add name wbd_sit0 "){link=true;return "",nil}
   if strings.HasPrefix(key,"link set dev wbd_sit0 "){return "",nil}
   if strings.HasPrefix(key,"-6 addr add "+p.local6()+"/128 "){addr=true;return "",nil}
   if len(a)>2&&a[2]=="show"{
    var rows []string
    for i,c:=range cmds{
     if !present[i]||c.tool!="ip"||c.kind!=a[0]||c.args[0]!=a[1]{continue}
     if a[1]=="route"{row:=strings.Join(c.args[1:]," ");if a[0]=="-6"{row+=" metric 1024 pref medium"};rows=append(rows,row)}else{
      row:=[]string{c.args[2]+":"}
      if c.args[3]!="from"{row=append(row,"from","all")}
      row=append(row,c.args[3:]...);rows=append(rows,strings.Join(row," "))
     }
    }
    return strings.Join(rows,"\n"),nil
   }
   if len(a)>3{
    for i,c:=range cmds{if c.tool=="ip"&&c.kind==a[0]&&c.args[0]==a[1]&&strings.Join(c.args[1:]," ")==strings.Join(a[3:]," "){present[i]=a[2]=="add";return "",nil}}
   }
   return "",fmt.Errorf("unexpected ip %q",a)
  }
  fw:=func(family string)Runner{return func(a ...string)(string,error){
   if a[4]=="-S"{
    var rows []string
    for i,c:=range cmds{if present[i]&&c.tool==family&&c.kind==a[3]&&c.args[0]==a[5]{rows=append(rows,"-A "+strings.Join(c.args," "))}}
    return strings.Join(rows,"\n"),nil
   }
   row:=a[5:];if a[4]=="-I"{row=append([]string{a[5]},a[7:]...)}
   for i,c:=range cmds{if c.tool==family&&c.kind==a[3]&&strings.Join(c.args," ")==strings.Join(row," "){present[i]=a[4]=="-I";return "",nil}}
   return "",fmt.Errorf("unexpected firewall %q",a)
  }}
  path:=filepath.Join(t.TempDir(),"owned",ipv6CarrierJournal)
  calls:=0
  batch:=func(rows [][]string)error{calls++;for _,row:=range rows{if _,e:=ip(row...);e!=nil{return e}};return nil}
  owner,e:=NewIPv6CarrierBatch(ip,fw("fw4"),fw("fw6"),batch,path,p);if e!=nil{t.Fatal(e)}
  if calls!=1{t.Fatal("cold FIB not one batch seam",calls)}
  for i,v:=range present{if !v{t.Fatal("missing",i)}}
  if !server{
   if !strings.Contains(strings.Join(cmds[len(cmds)-1].args," "),"uidrange 11201-11201"){t.Fatal("wrong UID")}
   proof,forward,nat,direct:=false,0,0,0
   for _,c:=range cmds{
    line:=strings.Join(c.args," ")
    if strings.Contains(line,"pref 9597 from "+p.local6()+"/128 to "+p.gateway6()+"/128 uidrange 0-0"){proof=true}
    if strings.Contains(line,"from 2001:db8:1234::/64 iif ap0")||strings.Contains(line,"from fd12:3456:789a::/64 iif ap0"){forward++}
    if strings.Contains(line,"--to-source "+p.local6()){nat++}
    if strings.HasPrefix(line,"route throw "){direct++;if strings.Contains(line,"2001:db8:1234::/64"){t.Fatal("throw replaced downstream route")}}
   }
   if !proof{t.Fatal("missing exact cold root peer route")}
   if tether&&direct!=2{t.Fatal("missing IPv6 direct routes",direct)}
   if tether&&(forward!=2||nat!=2){t.Fatal("missing IPv6 downstream prefixes",forward,nat)}
   if !tether&&(forward!=0||nat!=0){t.Fatal("unselected downstream captured")}
  }
  if e=owner.Stop();e!=nil{t.Fatal(e)}
  for _,v:=range present{if v{t.Fatal("Stop retained rule")}}
  owner,e=NewIPv6CarrierBatch(ip,fw("fw4"),fw("fw6"),batch,path,p);if e!=nil{t.Fatal(e)}
  owner.lock.Close();owner.lock=nil
  if e=RecoverIPv6CarrierBatch(ip,fw("fw4"),fw("fw6"),batch,path);e!=nil{t.Fatal(e)}
  if link||addr{t.Fatal("Restore retained link")}
  for _,v:=range present{if v{t.Fatal("Restore retained rule")}}
 }
}
