package rootjournal

import (
 "fmt"
 "path/filepath"
 "strings"
 "testing"
)
func TestB66SystemDNSSelectedUIDRouteAndRestore(t *testing.T){
 p:=SystemDNSPlan{DNSPlan:DNSPlan{Version:1,Tun:"wbdv40",Lease:"10.66.0.8/32",Port:43210,
  Tunnel:true,All:true,ExcludedAppIDs:[]int{11200,11201}},NetID:105}
 var link,route bool
 rules,nat:=map[string]string{},map[string]string{}
 ip:=func(args ...string)(string,error){
  k:=strings.Join(args," ")
  switch k{
  case "-d -o link show":if link{return "9: wbd_dns0: <UP> mtu 1500 alias "+systemDNSMarker+" dummy ",nil};return "",nil
  case "link add name wbd_dns0 alias "+systemDNSMarker+" type dummy":link=true;return "",nil
  case "link set dev wbd_dns0 up":return "",nil
  case "link del dev wbd_dns0":link=false;return "",nil
  case "-4 route show table all":if route{return "default dev wbd_dns0 table 19845 scope link src 10.66.0.8\n",nil};return "",nil
  case strings.Join(p.route("add")," "):route=true;return "",nil
  case strings.Join(p.route("del")," "):route=false;return "",nil
  case "-4 rule show":var rows []string;for _,r:=range rules{rows=append(rows,r)};return strings.Join(rows,"\n"),nil
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
   if r[0]=="-A"{nat[key]=strings.Join(row," ")}else{delete(nat,key)}
  };return nil
 }
 path:=filepath.Join(t.TempDir(),"owned","system-dns-journal.json")
 s,e:=NewSystemDNS(ip,fw,batchIP,batchNAT,path,p);if e!=nil{t.Fatal(e)}
 if !link||!route||len(nat)!=2||len(rules)!=2*len(p.ranges()){t.Fatal("missing exact kernel capture")}
 for _,line:=range rules{
  if !strings.Contains(line,"fwmark 0x69/0xffff")||!strings.Contains(line,"dport 53")||
     strings.Contains(line,"uidrange 0-0"){t.Fatal("scope escaped selected DNS",line)}
 }
 if e=s.Stop();e!=nil{t.Fatal(e)}
 if link||route||len(nat)!=0||len(rules)!=0{t.Fatal("Stop leaked")}
 s,e=NewSystemDNS(ip,fw,batchIP,batchNAT,path,p);if e!=nil{t.Fatal(e)}
 s.lock.Close();s.lock=nil
 if e=RecoverSystemDNS(ip,fw,batchIP,batchNAT,path);e!=nil{t.Fatal(e)}
 if link||route||len(nat)!=0||len(rules)!=0{t.Fatal("Restore leaked")}
}
