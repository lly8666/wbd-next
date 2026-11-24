package rootjournal

import (
 "encoding/json"
 "errors"
 "fmt"
 "io"
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

// The original resolver chowns DNS sockets to the requesting App on
// modern Android. Linux RPDB uidrange uses sk_uid; xt_owner uses the
// creator's credentials. A dedicated dummy output interface transfers
// that exact kernel selection to NAT without matching all root traffic.
type SystemDNSPlan struct{
 DNSPlan
 NetID uint32
}
func(p SystemDNSPlan) valid()bool{return p.DNSPlan.valid()&&p.NetID>0&&p.NetID<=65535&&p.Tun!=systemDNSIface}
func(p SystemDNSPlan) mark()string{return fmt.Sprintf("0x%x/0xffff",p.NetID)}
func(p SystemDNSPlan) rules(action string)[][]string{
 var out [][]string
 for i,r:=range p.ranges(){
  for k,proto:=range []string{"udp","tcp"}{
   out=append(out,[]string{"-4","rule",action,"pref",strconv.Itoa(systemDNSPref+2*i+k),
    "iif","lo","fwmark",p.mark(),"uidrange",fmt.Sprintf("%d-%d",r.from,r.to),
    "ipproto",proto,"dport","53","lookup",systemDNSTable})
  }
 }
 return out
}
func(p SystemDNSPlan) route(action string)[]string{
 return []string{"-4","route",action,"default","dev",systemDNSIface,"src",strings.TrimSuffix(p.Lease,"/32"),"table",systemDNSTable}
}
func(p SystemDNSPlan) nat(action string)[][]string{
 var rows [][]string
 for _,proto:=range []string{"udp","tcp"}{
  rows=append(rows,[]string{action,"OUTPUT","-o",systemDNSIface,"-p",proto,"-m",proto,
   "--dport","53","-m","comment","--comment",systemDNSMarker,"-j","REDIRECT","--to-ports",strconv.Itoa(p.Port)})
 }
 return rows
}
type systemDNSState struct{link,route bool;rules,nat [][]string}
type SystemDNSOwner struct{
 ip,fw Runner
 batchIP func([][]string)error
 batchNAT func([][]string)error
 lock *os.File
 path string
 plan SystemDNSPlan
}
func systemRuleKey(w []string)(string,error){
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
    fields["dport"]!="53"||fields["lookup"]!=systemDNSTable{
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
  if len(w)<2||w[1]!=systemDNSIface+":"{continue}
  if x.link||!strings.Contains(" "+line+" "," alias "+systemDNSMarker+" ")||
   !strings.Contains(" "+line+" "," dummy "){return x,fmt.Errorf("foreign DNS capture interface")}
  x.link=true
 }
 routes,e:=s.ip("-4","route","show","table","all");if e!=nil{return x,e}
 for _,line:=range strings.Split(routes,"\n"){
  w:=strings.Fields(line);found:=false
  for i:=0;i+1<len(w);i++{if w[i]=="table"&&w[i+1]==systemDNSTable{found=true}}
  if !found{continue}
  if x.route||len(w)<7||w[0]!="default"||w[1]!="dev"||w[2]!=systemDNSIface{return x,fmt.Errorf("foreign system DNS table")}
  fields:=map[string]string{}
  for i:=3;i<len(w);{
   if w[i]=="linkdown"{i++;continue}
   if i+1>=len(w){return x,fmt.Errorf("bad DNS route attribute")}
   if _,yes:=fields[w[i]];yes{return x,fmt.Errorf("duplicate DNS route attribute")}
   fields[w[i]]=w[i+1];i+=2
  }
  if fields["table"]!=systemDNSTable||fields["src"]!=strings.TrimSuffix(p.Lease,"/32"){
   return x,fmt.Errorf("foreign system DNS source route")
  }
  for k,v:=range fields{
   if k!="src"&&k!="table"&&!(k=="scope"&&v=="link")&&!(k=="proto"&&v=="boot"){
    return x,fmt.Errorf("foreign DNS route attribute")
   }
  }
  x.route=true
 }
 expected:=map[string][]string{}
 for _,r:=range p.rules("add"){
  row:=append([]string{r[4]+":","from","all"},r[5:]...)
  key,e:=systemRuleKey(row);if e!=nil{return x,e};expected[key]=r
 }
 rules,e:=s.ip("-4","rule","show");if e!=nil{return x,e}
 for _,line:=range strings.Split(rules,"\n"){
  w:=strings.Fields(line);if len(w)==0{continue}
  n,_:=strconv.Atoi(strings.TrimSuffix(w[0],":"))
  found:=n>=systemDNSPref&&n<systemDNSPref+2*AllMaxRules
  for i:=0;i+1<len(w);i++{if (w[i]=="lookup"||w[i]=="table")&&w[i+1]==systemDNSTable{found=true}}
  if !found{continue}
  key,e:=systemRuleKey(w);if e!=nil{return x,e}
  row,ok:=expected[key];if !ok{return x,fmt.Errorf("foreign system DNS UID rule")}
  delete(expected,key);x.rules=append(x.rules,row)
 }
 natExpected:=map[string][]string{}
 for _,row:=range p.nat("-A"){key,_:=dnsNATKey(row);natExpected[key]=row}
 nat,e:=s.fw("-w","2","-t","nat","-S","OUTPUT");if e!=nil{return x,e}
 for _,line:=range strings.Split(nat,"\n"){
  if !strings.Contains(line,systemDNSMarker){continue}
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
 if x.link{if _,e=s.ip("link","del","dev",systemDNSIface);e!=nil{return e}}
 x,e=s.state(p);if e!=nil{return e}
 if x.link||x.route||len(x.rules)!=0||len(x.nat)!=0{return fmt.Errorf("system DNS Stop readback incomplete")}
 if e=os.Remove(s.path);e!=nil{return e};return parentSync(s.path)
}
func RecoverSystemDNS(ip,fw Runner,batchIP,batchNAT func([][]string)error,path string)error{
 l,e:=scopedOwnerLock(path,systemDNSJournal,"system-dns-owner.lock");if e!=nil{return e};defer l.Close()
 p,found,e:=readSystemDNS(path);if e!=nil||!found{return e}
 return (&SystemDNSOwner{ip:ip,fw:fw,batchIP:batchIP,batchNAT:batchNAT,path:path}).remove(p)
}
func NewSystemDNS(ip,fw Runner,batchIP,batchNAT func([][]string)error,path string,p SystemDNSPlan)(*SystemDNSOwner,error){
 p.Version=1
 if ip==nil||fw==nil||!p.valid(){return nil,fmt.Errorf("invalid system DNS scope")}
 l,e:=scopedOwnerLock(path,systemDNSJournal,"system-dns-owner.lock");if e!=nil{return nil,e}
 s:=&SystemDNSOwner{ip:ip,fw:fw,batchIP:batchIP,batchNAT:batchNAT,path:path,lock:l,plan:p}
 fail:=func(e error)(*SystemDNSOwner,error){l.Close();return nil,e}
 old,found,e:=readSystemDNS(path);if e!=nil{return fail(e)}
 if found{if e=s.remove(old);e!=nil{return fail(e)}}
 x,e:=s.state(p);if e!=nil{return fail(e)}
 if x.link||x.route||len(x.rules)!=0||len(x.nat)!=0{return fail(fmt.Errorf("system DNS state without journal"))}
 if e=writeSystemDNS(path,p);e!=nil{return fail(e)}
 rollback:=func(e error)(*SystemDNSOwner,error){return fail(errors.Join(e,s.remove(p)))}
 if _,e=ip("link","add","name",systemDNSIface,"alias",systemDNSMarker,"type","dummy");e!=nil{return rollback(e)}
 if _,e=ip("link","set","dev",systemDNSIface,"up");e!=nil{return rollback(e)}
 if _,e=ip(p.route("add")...);e!=nil{return rollback(e)}
 if e=s.changeNAT(p.nat("-A"),"-A");e!=nil{return rollback(e)}
 if e=s.changeRules(p.rules("add"),"add");e!=nil{return rollback(e)}
 x,e=s.state(p)
 if e!=nil||!x.link||!x.route||len(x.nat)!=2||len(x.rules)!=len(p.rules("add")){
  return rollback(errors.Join(e,fmt.Errorf("system DNS installation readback incomplete")))
 }
 return s,nil
}
func(s *SystemDNSOwner) Stop()error{
 if s.lock==nil{return nil}
 e:=s.remove(s.plan);e=errors.Join(e,s.lock.Close());s.lock=nil;return e
}
