package rootjournal

import (
 "errors"
 "os"
 "fmt"
 "path/filepath"
 "strings"
 "testing"
)
func TestB66SystemDNSSelectedUIDRouteAndRestore(t *testing.T){testSystemDNSOwner(t,false,false)}
func TestB69SystemDNS6SelectedUIDRouteAndRestore(t *testing.T){testSystemDNSOwner(t,true,false)}
func TestB94SystemDNSRuleIOOwnerRestore(t *testing.T){for _,v6:=range []bool{false,true}{testSystemDNSOwner(t,v6,true)}}
func testSystemDNSOwner(t *testing.T,v6,binaryRules bool){
 p:=SystemDNSPlan{DNSPlan:DNSPlan{Version:1,Tun:"wbdv40",Lease:"10.66.0.8/32",Port:43210,
  Tunnel:true,All:true,ExcludedAppIDs:[]int{11200,11201}},NetID:105,IPv6:v6}
 var link,route,addr,alias bool
 failNAT:=false
 rules,nat:=map[string]string{},map[string]string{}
 ip:=func(args ...string)(string,error){
  k:=strings.Join(args," ")
  switch k{
  case "-d -o link show":if link{marker:="";if alias{marker=" alias "+p.marker()};return "9: "+p.iface()+": <UP> mtu 1500"+marker+" dummy ",nil};return "",nil
  case "link add name "+p.iface()+" type dummy":link=true;return "",nil
  case "link set dev "+p.iface()+" alias "+p.marker():if !link{return "",fmt.Errorf("no dummy")};alias=true;return "",nil
  case "link set dev "+p.iface()+" up":return "",nil
  case "link del dev "+p.iface():link=false;addr=false;alias=false;return "",nil
  case "-6 -o addr show":if addr{return "9: "+p.iface()+" inet6 "+systemDNS6Address+"/128 scope global nodad noprefixroute",nil};return "",nil
  case "-6 addr add "+systemDNS6Address+"/128 dev "+p.iface()+" nodad noprefixroute":addr=true;return "",nil
  case p.family()+" route show table all":
   if route{
    line:="default dev "+p.iface()+" table "+p.table()+" src "+p.source()
    if p.IPv6{line+=" metric 1024 pref medium"}else{line+=" scope link"}
    return line+"\n",nil
   };return "",nil
  case strings.Join(p.route("add")," "):route=true;return "",nil
  case strings.Join(p.route("del")," "):route=false;return "",nil
  case p.family()+" rule show":var rows []string;for _,r:=range rules{rows=append(rows,r)};return strings.Join(rows,"\n"),nil
  }
  if len(args)>5&&args[1]=="rule"{
   pref:=args[4]
   if args[2]=="add"{rules[pref]=strings.Join(append([]string{pref+":","from","all"},args[5:]...)," ")}
   if args[2]=="del"{delete(rules,pref)}
   return "",nil
  }
  return "",fmt.Errorf("unexpected ip %q",args)
 }
 fw:=func(args ...string)(string,error){
  if strings.Join(args," ")!="-w 2 -t nat -S OUTPUT"{return "",fmt.Errorf("unexpected firewall")}
  var rows []string;for _,r:=range nat{rows=append(rows,r)};return strings.Join(rows,"\n"),nil
 }
 batchIP:=func(rows [][]string)error{for _,row:=range rows{if _,e:=ip(row...);e!=nil{return e}};return nil}
 batchNAT:=func(rows [][]string)error{
  for _,r:=range rows{row:=append([]string(nil),r...);row[0]="-A";key,_:=dnsNATKey(row)
   if r[0]=="-A"{if failNAT{return fmt.Errorf("kernel target unavailable")};nat[key]=strings.Join(row," ")}else{delete(nat,key)}
  };return nil
 }
 var transport *SystemDNSRuleIO
 var reads,changes int
 if binaryRules{transport=&SystemDNSRuleIO{Read:func(family string)(string,error){reads++;return ip(family,"rule","show")},Change:func(rows [][]string)error{changes++;return batchIP(rows)}}}
 path:=filepath.Join(t.TempDir(),"owned",p.journal())
 s,e:=NewSystemDNS(ip,fw,batchIP,batchNAT,path,p,transport);if e!=nil{t.Fatal(e)}
 if !link||!alias||!route||addr!=p.IPv6||len(nat)!=2||len(rules)!=2*len(p.ranges()){t.Fatal("missing exact kernel capture")}
 for _,line:=range rules{
  if !strings.Contains(line,"fwmark 0x69/0xffff")||!strings.Contains(line,"dport 53")||
     strings.Contains(line,"uidrange 0-0"){t.Fatal("scope escaped selected DNS",line)}
 }
 if e=s.Stop();e!=nil{t.Fatal(e)}
 if link||route||addr||len(nat)!=0||len(rules)!=0{t.Fatal("Stop leaked")}
 s,e=NewSystemDNS(ip,fw,batchIP,batchNAT,path,p,transport);if e!=nil{t.Fatal(e)}
 s.lock.Close();s.lock=nil
 if e=recoverSystemDNS(ip,fw,batchIP,batchNAT,path,v6,transport);e!=nil{t.Fatal(e)}
 if link||route||addr||len(nat)!=0||len(rules)!=0{t.Fatal("Restore leaked")}
 if binaryRules&&(reads==0||changes!=4){t.Fatalf("exact rule transport not used for Start/Stop/Restore: %d %d",reads,changes)}
 if v6{
  failNAT=true
  _,e=NewSystemDNS(ip,fw,batchIP,batchNAT,path,p,transport)
  var start *SystemDNSStartError
  if !errors.As(e,&start)||!start.Clean||start.Stage!="NAT"{t.Fatalf("expected verified DNS6 rollback: %v",e)}
  if link||route||addr||len(nat)!=0||len(rules)!=0{t.Fatal("failed start leaked")}
  if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatal("failed journal retained",e)}
 }
}

func TestB122DNS6NATCapabilityReadOnly(t *testing.T){
 for _,available:=range []bool{false,true}{
  calls:=0
  e:=ProbeSystemDNS6NAT(func(args ...string)(string,error){
   calls++
   if strings.Join(args," ")!="-w 2 -t nat -S OUTPUT"{t.Fatal(args)}
   if !available{return "",fmt.Errorf("nat table unavailable")};return "-P OUTPUT ACCEPT",nil
  })
  if (e==nil)!=available||calls!=1{t.Fatal("bad NAT6 probe",e,calls)}
 }
}
