package rootjournal

import (
 "fmt"
 "path/filepath"
 "reflect"
 "strings"
 "testing"
)

// Command seam models iptables/ip readback, NOT Android kernel traffic.
type b64DNSKernel struct{p DNSPlan;route,rule bool;rows []string}
func(k *b64DNSKernel) ip(args ...string)(string,error){
 switch{
 case reflect.DeepEqual(args,[]string{"-4","route","show","table","all"}):
  if k.route{return strings.TrimSuffix(k.p.upstream(),"/32")+" dev "+k.p.Tun+" table 19843 scope link\n",nil};return "",nil
 case reflect.DeepEqual(args,[]string{"-4","rule","show"}):
  if k.rule{return "9599: from "+k.p.Lease+" to "+strings.TrimSuffix(k.p.upstream(),"/32")+" uidrange 0-0 lookup 19843\n",nil};return "",nil
 case reflect.DeepEqual(args,dnsRoute(k.p,"add")):k.route=true
 case reflect.DeepEqual(args,dnsRoute(k.p,"del")):k.route=false
 case reflect.DeepEqual(args,dnsRule(k.p,"add")):k.rule=true
 case reflect.DeepEqual(args,dnsRule(k.p,"del")):k.rule=false
 default:return "",fmt.Errorf("unexpected ip command %q",args)
 };return "",nil
}
func(k *b64DNSKernel) fw(args ...string)(string,error){
 if reflect.DeepEqual(args,[]string{"-w","2","-t","nat","-S","OUTPUT"}){
  return strings.Join(k.rows,"\n"),nil
 }
 return "",fmt.Errorf("unexpected firewall command")
}
func(k *b64DNSKernel) batch(commands [][]string)error{
 for _,row:=range commands{
  if row[0]=="-A"{k.rows=append(k.rows,strings.Join(row," "));continue}
  copyRow:=append([]string(nil),row...);copyRow[0]="-A"
  want:=strings.Join(copyRow," ");found:=false
  for i,r:=range k.rows{if r==want{k.rows=append(k.rows[:i],k.rows[i+1:]...);found=true;break}}
  if !found{return fmt.Errorf("missing exact DNS NAT row")}
 };return nil
}
func TestB64OwnedTCPDNSSelectedAndAllAppRoutesRestore(t *testing.T){
 for _,all:=range []bool{false,true}{
  p:=DNSPlan{Version:1,Tun:"wbdv40",Lease:"10.66.0.8/32",Port:43210,Tunnel:true,
   UIDs:[]int{11200,11201},All:all}
  if all{p.UIDs=nil;p.ExcludedAppIDs=[]int{11200,11201,11500};p.TunnelUpstream="9.9.9.9"}
  k:=&b64DNSKernel{p:p}
  path:=filepath.Join(t.TempDir(),"owned","dns-tcp-journal.json")
  owner,e:=NewDNS(k.ip,k.fw,k.batch,path,p);if e!=nil{t.Fatal(e)}
  if !k.route||!k.rule||len(k.rows)!=len(p.ranges()){t.Fatal("missing owned DNS rule")}
  for _,row:=range k.rows{
   if !strings.Contains(row,"-o wbdv40 -p tcp")||!strings.Contains(row,"--dport 53")||
      !strings.Contains(row,"--uid-owner")||strings.Contains(row,"--uid-owner 0 "){
    t.Fatal("DNS scope escaped the actual original UID route",row)
   }
  }
  if e=RecoverDNS(k.ip,k.fw,k.batch,path);e==nil{t.Fatal("Restore stole active DNS owner")}
  // Real flock release simulates process death; exact durable cleanup.
  owner.lock.Close();owner.lock=nil
  if e=RecoverDNS(k.ip,k.fw,k.batch,path);e!=nil{t.Fatal(e)}
  if k.route||k.rule||len(k.rows)!=0{t.Fatal("DNS kernel state retained")}
 }
}
