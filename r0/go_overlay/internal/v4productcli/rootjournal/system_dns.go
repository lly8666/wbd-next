package rootjournal

import (
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/netip"
 "os"
 "strconv"
 "strings"
 "syscall"
)

const systemDNSTable="19845"
const systemDNSIface="wbd_dns0"
const systemDNSMarker="wbd-next-root-system-dns-v1"
const systemDNSJournal="system-dns-journal.json"
const systemDNSPref=9100
const systemDNS6Address="fd65:5742:444e:5300::1"

// The original resolver chowns DNS sockets to the requesting App on
// modern Android. Linux RPDB uidrange uses sk_uid; xt_owner uses the
// creator's credentials. A dedicated dummy output interface transfers
// that exact kernel selection to NAT without matching all root traffic.
type SystemDNSPlan struct{
 DNSPlan
 NetID uint32
 IPv6 bool // separate opt-in journal; old v4 journal defaults false
}
func(p SystemDNSPlan) family()string{if p.IPv6{return "-6"};return "-4"}
func(p SystemDNSPlan) iface()string{if p.IPv6{return "wbd_dns6"};return systemDNSIface}
func(p SystemDNSPlan) table()string{if p.IPv6{return "19846"};return systemDNSTable}
func(p SystemDNSPlan) marker()string{if p.IPv6{return "wbd-next-root-system-dns6-v1"};return systemDNSMarker}
func(p SystemDNSPlan) source()string{if p.IPv6{return systemDNS6Address};return strings.TrimSuffix(p.Lease,"/32")}
func(p SystemDNSPlan) journal()string{if p.IPv6{return "system-dns6-journal.json"};return systemDNSJournal}
func(p SystemDNSPlan) lockName()string{if p.IPv6{return "system-dns6-owner.lock"};return "system-dns-owner.lock"}
func(p SystemDNSPlan) valid()bool{return p.DNSPlan.valid()&&p.NetID>0&&p.NetID<=65535&&p.Tun!=systemDNSIface&&p.Tun!="wbd_dns6"}
func(p SystemDNSPlan) mark()string{return fmt.Sprintf("0x%x/0xffff",p.NetID)}
func(p SystemDNSPlan) rules(action string)[][]string{
 var out [][]string
 for i,r:=range p.ranges(){
  for k,proto:=range []string{"udp","tcp"}{
   out=append(out,[]string{p.family(),"rule",action,"pref",strconv.Itoa(systemDNSPref+2*i+k),
    "iif","lo","fwmark",p.mark(),"uidrange",fmt.Sprintf("%d-%d",r.from,r.to),
    "ipproto",proto,"dport","53","lookup",p.table()})
  }
 }
 return out
}
func(p SystemDNSPlan) route(action string)[]string{
 return []string{p.family(),"route",action,"default","dev",p.iface(),"src",p.source(),"table",p.table()}
}
func(p SystemDNSPlan) nat(action string)[][]string{
 var rows [][]string
 for _,proto:=range []string{"udp","tcp"}{
  rows=append(rows,[]string{action,"OUTPUT","-o",p.iface(),"-p",proto,"-m",proto,
   "--dport","53","-m","comment","--comment",p.marker(),"-j","REDIRECT","--to-ports",strconv.Itoa(p.Port)})
 }
 return rows
}
type systemDNSState struct{link,route,addr bool;rules,nat [][]string}
// Optional exact kernel rule transport; the host fake runners retain the
// original textual path. Only system DNS uses this cold control interface.
type SystemDNSRuleIO struct {
 Read func(string)(string,error)
 Change func([][]string)error
}
func systemDNSIO(v []*SystemDNSRuleIO)*SystemDNSRuleIO{if len(v)>0{return v[0]};return nil}
type SystemDNSOwner struct{
 ip,fw Runner
 ruleIO *SystemDNSRuleIO
 batchIP func([][]string)error
 batchNAT func([][]string)error
 lock *os.File
 path string
 plan SystemDNSPlan
}
func systemRuleKey(w []string,table string)(string,error){
 if len(w)<1{return "",fmt.Errorf("empty system DNS rule")}
 pref:=strings.TrimSuffix(w[0],":")
 fields:=map[string]string{}
 for i:=1;i<len(w);i+=2{
  if i+1>=len(w){return "",fmt.Errorf("bad system DNS rule")}
  k,v:=w[i],w[i+1]
  if k=="table"{k="lookup"}
  if _,yes:=fields[k];yes{return "",fmt.Errorf("duplicate selector")}
  fields[k]=v
 }
 if fields["from"]!="all"||len(fields)!=7||fields["iif"]!="lo"||
    fields["dport"]!="53"||fields["lookup"]!=table{
  return "",fmt.Errorf("foreign system DNS selector")
 }
 proto:=fields["ipproto"]
 if proto=="17"{proto="udp"};if proto=="6"{proto="tcp"}
 mark:=strings.Split(fields["fwmark"],"/")
 if len(mark)!=2{return "",fmt.Errorf("invalid system DNS mark")}
 v,e:=strconv.ParseUint(mark[0],0,32);m,f:=strconv.ParseUint(mark[1],0,32)
 if e!=nil||f!=nil||m!=65535||v==0||v>65535{return "",fmt.Errorf("invalid system DNS netid")}
 return fmt.Sprintf("%s|%x|%s|%s",pref,v,fields["uidrange"],proto),nil
}
func(s *SystemDNSOwner) state(p SystemDNSPlan)(systemDNSState,error){
 var x systemDNSState
 links,e:=s.ip("-d","-o","link","show");if e!=nil{return x,e}
 for _,line:=range strings.Split(links,"\n"){
  w:=strings.Fields(line)
  if len(w)<2||w[1]!=p.iface()+":"{continue}
  if x.link||!strings.Contains(" "+line+" "," alias "+p.marker()+" ")||
   !strings.Contains(" "+line+" "," dummy "){return x,fmt.Errorf("foreign DNS capture interface")}
  x.link=true
 }
 if p.IPv6{
  addresses,e:=s.ip("-6","-o","addr","show");if e!=nil{return x,e}
  for _,line:=range strings.Split(addresses,"\n"){
   w:=strings.Fields(line)
   if len(w)<4||w[2]!="inet6"{continue}
   iface:=strings.TrimSuffix(w[1],"\\")
   addr,err:=netip.ParsePrefix(w[3]);if err!=nil{continue}
   if addr.Addr().String()==systemDNS6Address{
    if x.addr||!x.link||iface!=p.iface()||addr.Bits()!=128{return x,fmt.Errorf("foreign system DNS6 address")}
    for _,flag:=range w[4:]{if flag=="tentative"||flag=="dadfailed"{return x,fmt.Errorf("DNS6 address not usable")}}
    x.addr=true
   }else if iface==p.iface()&&!addr.Addr().IsLinkLocalUnicast(){
    return x,fmt.Errorf("foreign address on DNS6 interface")
   }
  }
 }
 routes,e:=s.ip(p.family(),"route","show","table","all");if e!=nil{return x,e}
 for _,line:=range strings.Split(routes,"\n"){
  w:=strings.Fields(line);found:=false
  for i:=0;i+1<len(w);i++{if w[i]=="table"&&w[i+1]==p.table(){found=true}}
  if !found{continue}
  if x.route||len(w)<7||w[0]!="default"||w[1]!="dev"||w[2]!=p.iface(){return x,fmt.Errorf("foreign system DNS table")}
  fields:=map[string]string{}
  for i:=3;i<len(w);{
   if w[i]=="linkdown"{i++;continue}
   if i+1>=len(w){return x,fmt.Errorf("bad DNS route attribute")}
   if _,yes:=fields[w[i]];yes{return x,fmt.Errorf("duplicate DNS route attribute")}
   fields[w[i]]=w[i+1];i+=2
  }
  if fields["table"]!=p.table()||fields["src"]!=p.source(){
   return x,fmt.Errorf("foreign system DNS source route")
  }
  for k,v:=range fields{
   if p.IPv6&&((k=="metric"&&v=="1024")||(k=="pref"&&v=="medium")||(k=="proto"&&v=="static")){continue}
   if k!="src"&&k!="table"&&!(k=="scope"&&v=="link")&&!(k=="proto"&&v=="boot"){
    return x,fmt.Errorf("foreign DNS route attribute")
   }
  }
  x.route=true
 }
 expected:=map[string][]string{}
 for _,r:=range p.rules("add"){
  row:=append([]string{r[4]+":","from","all"},r[5:]...)
  key,e:=systemRuleKey(row,p.table());if e!=nil{return x,e};expected[key]=r
 }
 var rules string
 if s.ruleIO!=nil{rules,e=s.ruleIO.Read(p.family())}else{rules,e=s.ip(p.family(),"rule","show")}
 if e!=nil{return x,e}
 for _,line:=range strings.Split(rules,"\n"){
  w:=strings.Fields(line);if len(w)==0{continue}
  n,_:=strconv.Atoi(strings.TrimSuffix(w[0],":"))
  found:=n>=systemDNSPref&&n<systemDNSPref+2*AllMaxRules
  for i:=0;i+1<len(w);i++{if (w[i]=="lookup"||w[i]=="table")&&w[i+1]==p.table(){found=true}}
  if !found{continue}
  key,e:=systemRuleKey(w,p.table());if e!=nil{return x,e}
  row,ok:=expected[key];if !ok{return x,fmt.Errorf("foreign system DNS UID rule")}
  delete(expected,key);x.rules=append(x.rules,row)
 }
 natExpected:=map[string][]string{}
 for _,row:=range p.nat("-A"){key,_:=dnsNATKey(row);natExpected[key]=row}
 nat,e:=s.fw("-w","2","-t","nat","-S","OUTPUT");if e!=nil{return x,e}
 for _,line:=range strings.Split(nat,"\n"){
  if !strings.Contains(line,p.marker()){continue}
  key,e:=dnsNATKey(strings.Fields(line));if e!=nil{return x,e}
  row,ok:=natExpected[key];if !ok{return x,fmt.Errorf("foreign system DNS NAT")}
  delete(natExpected,key);x.nat=append(x.nat,row)
 }
 return x,nil
}
func(s *SystemDNSOwner) changeRules(rows [][]string,action string)error{
 if len(rows)==0{return nil}
 var cmds [][]string
 for _,row:=range rows{
  copyRow:=append([]string(nil),row...);copyRow[2]=action;cmds=append(cmds,copyRow)
 }
 if s.ruleIO!=nil{return s.ruleIO.Change(cmds)}
 if s.batchIP!=nil{return s.batchIP(cmds)}
 for _,row:=range cmds{if _,e:=s.ip(row...);e!=nil{return e}}
 return nil
}
func(s *SystemDNSOwner) changeNAT(rows [][]string,action string)error{
 d:=DNSOwner{firewall:s.fw,batch:s.batchNAT}
 return d.changeNAT(rows,action)
}
func readSystemDNS(path string)(SystemDNSPlan,bool,error){
 var p SystemDNSPlan
 f,e:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(e,syscall.ENOENT){return p,false,nil}
 if e!=nil{return p,false,e};defer f.Close()
 st,e:=f.Stat();if e!=nil{return p,false,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||owner.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||
    st.Mode().Perm()!=0600||st.Size()>maxJournalBytes{return p,false,fmt.Errorf("invalid system DNS journal")}
 d:=json.NewDecoder(io.LimitReader(f,maxJournalBytes+1));d.DisallowUnknownFields()
 if d.Decode(&p)!=nil||!p.valid()||d.Decode(&struct{}{})!=io.EOF{return p,false,fmt.Errorf("invalid system DNS record")}
 return p,true,nil
}
func writeSystemDNS(path string,p SystemDNSPlan)error{
 b,e:=json.Marshal(p);if e!=nil{return e}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600);if e!=nil{return e}
 n,e:=f.Write(b);if e==nil&&n!=len(b){e=io.ErrShortWrite};if e==nil{e=f.Sync()}
 if e=errors.Join(e,f.Close());e!=nil{return e};return parentSync(path)
}
func(s *SystemDNSOwner) remove(p SystemDNSPlan)error{
 x,e:=s.state(p);if e!=nil{return e}
 // Withdraw the exact uidrange routing before removing the local redirect.
 if e=s.changeRules(x.rules,"del");e!=nil{return e}
 if e=s.changeNAT(x.nat,"-D");e!=nil{return e}
 if x.route{if _,e=s.ip(p.route("del")...);e!=nil{return e}}
 if x.link{if _,e=s.ip("link","del","dev",p.iface());e!=nil{return e}}
 x,e=s.state(p);if e!=nil{return e}
 if x.link||x.route||x.addr||len(x.rules)!=0||len(x.nat)!=0{return fmt.Errorf("system DNS Stop readback incomplete")}
 if e=os.Remove(s.path);e!=nil{return e};return parentSync(s.path)
}
func RecoverSystemDNS(ip,fw Runner,batchIP,batchNAT func([][]string)error,path string,ruleIO ...*SystemDNSRuleIO)error{
 return recoverSystemDNS(ip,fw,batchIP,batchNAT,path,false,ruleIO...)
}
func RecoverSystemDNS6(ip,fw Runner,batchIP,batchNAT func([][]string)error,path string,ruleIO ...*SystemDNSRuleIO)error{
 return recoverSystemDNS(ip,fw,batchIP,batchNAT,path,true,ruleIO...)
}
func recoverSystemDNS(ip,fw Runner,batchIP,batchNAT func([][]string)error,path string,v6 bool,ruleIO ...*SystemDNSRuleIO)error{
 scope:=SystemDNSPlan{IPv6:v6}
 l,e:=scopedOwnerLock(path,scope.journal(),scope.lockName());if e!=nil{return e};defer l.Close()
 p,found,e:=readSystemDNS(path);if e!=nil||!found{return e}
 if p.IPv6!=v6{return fmt.Errorf("system DNS journal family mismatch")}
 return (&SystemDNSOwner{ip:ip,fw:fw,batchIP:batchIP,batchNAT:batchNAT,path:path,ruleIO:systemDNSIO(ruleIO)}).remove(p)
}
func NewSystemDNS(ip,fw Runner,batchIP,batchNAT func([][]string)error,path string,p SystemDNSPlan,ruleIO ...*SystemDNSRuleIO)(*SystemDNSOwner,error){
 p.Version=1
 if ip==nil||fw==nil||!p.valid(){return nil,fmt.Errorf("invalid system DNS scope")}
 l,e:=scopedOwnerLock(path,p.journal(),p.lockName());if e!=nil{return nil,e}
 s:=&SystemDNSOwner{ip:ip,fw:fw,batchIP:batchIP,batchNAT:batchNAT,path:path,lock:l,plan:p,ruleIO:systemDNSIO(ruleIO)}
 fail:=func(e error)(*SystemDNSOwner,error){l.Close();return nil,e}
 old,found,e:=readSystemDNS(path);if e!=nil{return fail(e)}
 if found{if old.IPv6!=p.IPv6{return fail(fmt.Errorf("system DNS journal family mismatch"))};if e=s.remove(old);e!=nil{return fail(e)}}
 x,e:=s.state(p);if e!=nil{return fail(e)}
 if x.link||x.route||x.addr||len(x.rules)!=0||len(x.nat)!=0{return fail(fmt.Errorf("system DNS state without journal"))}
 if e=writeSystemDNS(path,p);e!=nil{return fail(e)}
 rollback:=func(e error)(*SystemDNSOwner,error){return fail(errors.Join(e,s.remove(p)))}
 // Android ip requires the dummy type during creation. Set the existing
 // alias before installing routes/NAT; this remains cold-only.
 if _,e=ip("link","add","name",p.iface(),"type","dummy");e!=nil{return rollback(e)}
 if _,e=ip("link","set","dev",p.iface(),"alias",p.marker());e!=nil{
  _,removeErr:=ip("link","del","dev",p.iface())
  return rollback(errors.Join(e,removeErr))
 }
 if _,e=ip("link","set","dev",p.iface(),"up");e!=nil{return rollback(e)}
 if p.IPv6{
  if _,e=ip("-6","addr","add",systemDNS6Address+"/128","dev",p.iface(),"nodad","noprefixroute");e!=nil{return rollback(e)}
 }
 if _,e=ip(p.route("add")...);e!=nil{return rollback(e)}
 if e=s.changeNAT(p.nat("-A"),"-A");e!=nil{return rollback(e)}
 if e=s.changeRules(p.rules("add"),"add");e!=nil{return rollback(e)}
 x,e=s.state(p)
 if e!=nil||!x.link||!x.route||x.addr!=p.IPv6||len(x.nat)!=2||len(x.rules)!=len(p.rules("add")){
  return rollback(errors.Join(e,fmt.Errorf("system DNS installation readback incomplete")))
 }
 return s,nil
}
func(s *SystemDNSOwner) Stop()error{
 if s.lock==nil{return nil}
 e:=s.remove(s.plan);e=errors.Join(e,s.lock.Close());s.lock=nil;return e
}
