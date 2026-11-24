package rootjournal

import (
 "fmt"
 "path/filepath"
 "strings"
 "testing"
)
func TestB65TetherOwnedForwardingAndRestore(t *testing.T){testTetherOwner(t,false)}
func TestB68TetherDNSExactDownstreamAndRestore(t *testing.T){testTetherOwner(t,true)}
func TestB76TetherIPv4DirectCIDRsAndRestore(t *testing.T){testTetherOwner(t,true,true)}
func TestB82TetherCountryIPv4BatchAndRestore(t *testing.T){testTetherOwner(t,true,true,true)}
func testTetherOwner(t *testing.T,withDNS bool,direct ...bool){
 p:=TetherPlan{Version:1,Tun:"wbd0",Downstream:"ap0",Subnet:"192.168.43.0/24",Lease:"10.9.0.2/32"}
 if withDNS{p.DNSAddress="192.168.43.1";p.DNSPort=43210}
 if len(direct)>0&&direct[0]{p.DirectCIDRs=[]string{"10.0.0.0/8","192.168.43.0/24","192.168.43.7/32","192.168.50.0/24"}}
 country:=len(direct)>1&&direct[1]
 if country{
  // Real merged parser, normal-sized prefix table rather than subprocess-per-prefix.
  var snapshot []string
  for i:=0;i<128;i++{snapshot=append(snapshot,fmt.Sprintf("100.%d.0.0/16",i))}
  var err error
  p.DirectCIDRs,err=MergeCountryDirectCIDRs(p.DirectCIDRs,strings.Join(snapshot,"\n"),"")
  if err!=nil{t.Fatal(err)}
 }
 if withDNS{
  count:=0
  for _,c:=range p.commands(){
   if c.args[0]!="PREROUTING"{continue}
   if !strings.Contains(strings.Join(c.args," "),"-i ap0 -s 192.168.43.0/24")||
      !strings.Contains(strings.Join(c.args," "),"--dport 53")||
      !strings.Contains(strings.Join(c.args," "),"--to-destination 192.168.43.1:43210"){
    t.Fatal("DNS capture escaped exact tether scope")
   };count++
  }
  if count!=2{t.Fatal("missing UDP or TCP DNS")}
 }
 cmds:=p.commands();present:=make([]bool,len(cmds))
 if len(direct)>0&&direct[0]{count:=0;for _,c:=range cmds{if c.kind=="route"&&c.args[0]=="throw"{count++;if strings.HasPrefix(c.args[1],"192.168.43."){t.Fatal("downstream return route bypassed")}}};expected:=2;if country{expected+=128};if count!=expected{t.Fatal("missing shared IPv4 direct route",count)}}
 ip:=func(a ...string)(string,error){
  if a[2]=="show"{
   var lines []string
   for i,c:=range cmds{if !present[i]||c.kind!=a[1]{continue}
    if c.kind=="route"{lines=append(lines,strings.Join(c.args," ")+" scope link")}else{
     row:=append([]string{c.args[1]+":"},c.args[2:]...)
     if i==5{row=append([]string{c.args[1]+":","from","all"},c.args[2:]...)}
     lines=append(lines,strings.Join(row," "))
    }
   };return strings.Join(lines,"\n"),nil
  }
  for i,c:=range cmds{if c.kind==a[1]&&strings.Join(c.args," ")==strings.Join(a[3:]," "){present[i]=a[2]=="add";return "",nil}}
  return "",fmt.Errorf("unexpected ip %v",a)
 }
 fw:=func(a ...string)(string,error){
  if a[4]=="-S"{var lines []string;for i,c:=range cmds{if present[i]&&c.kind==a[3]&&c.args[0]==a[5]{lines=append(lines,"-A "+strings.Join(c.args," "))}};return strings.Join(lines,"\n"),nil}
  row:=a[5:];if a[4]=="-I"{row=append([]string{a[5]},a[7:]...)}
  for i,c:=range cmds{if c.kind==a[3]&&strings.Join(c.args," ")==strings.Join(row," "){present[i]=a[4]=="-I";return "",nil}}
  return "",fmt.Errorf("unexpected firewall %v",a)
 }
 path:=filepath.Join(t.TempDir(),"owned","tether-journal.json")
 var batches []DirectBatch
 calls:=0
 if country{batches=append(batches,func(rows [][]string)error{
  calls++
  if len(rows)<128{return fmt.Errorf("country routes were not batched")}
  for _,row:=range rows{if _,e:=ip(row...);e!=nil{return e}}
  return nil
 })}
 owner,e:=NewTether(ip,fw,path,p,batches...);if e!=nil{t.Fatal(e)}
 for i,v:=range present{if !v{t.Fatalf("missing command %d",i)}}
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 for _,v:=range present{if v{t.Fatal("Stop retained state")}}
 owner,e=NewTether(ip,fw,path,p,batches...);if e!=nil{t.Fatal(e)}
 if e=owner.lock.Close();e!=nil{t.Fatal(e)};owner.lock=nil
 if e=RecoverTether(ip,fw,path,batches...);e!=nil{t.Fatal(e)}
 for _,v:=range present{if v{t.Fatal("Restore retained state")}}
 if country&&calls!=4{t.Fatal("expected one route batch for each START/STOP/Restore",calls)}
}
