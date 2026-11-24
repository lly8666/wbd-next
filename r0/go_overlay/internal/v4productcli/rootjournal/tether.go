package rootjournal

import (
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/netip"
 "os"
 "sort"
 "strconv"
 "strings"
 "syscall"
)

const tetherTable="19844"
const tetherMarker="wbd-next-root-tether-v1"
const tetherJournal="tether-journal.json"

type TetherPlan struct {
 Version int
 Tun,Downstream,Subnet,Lease string
 DNSAddress string
 DNSPort int
}
func(p TetherPlan) valid()bool{
 s,e:=netip.ParsePrefix(p.Subnet)
 l,f:=netip.ParsePrefix(p.Lease)
 if p.DNSPort!=0||p.DNSAddress!=""{
  a,err:=netip.ParseAddr(p.DNSAddress)
  if err!=nil||p.DNSPort<1||p.DNSPort>65535||!a.Is4()||!s.Contains(a)||a==s.Addr(){return false}
 }
 return p.Version==1&&nameOK(p.Tun)&&nameOK(p.Downstream)&&p.Tun!=p.Downstream&&
 e==nil&&f==nil&&s.Addr().Is4()&&s.Addr().IsPrivate()&&s==s.Masked()&&s.Bits()>=8&&s.Bits()<=30&&
 l.Addr().Is4()&&l.Bits()==32&&!l.Addr().IsUnspecified()&&!l.Addr().IsMulticast()&&!s.Contains(l.Addr())
}
type tetherCommand struct{ kind string; args []string }
func(p TetherPlan) commands()[]tetherCommand{
 lease:=strings.TrimSuffix(p.Lease,"/32")
 out:=[]tetherCommand{
  {"route",[]string{"default","dev",p.Tun,"table",tetherTable}},
  {"route",[]string{p.Subnet,"dev",p.Downstream,"table",tetherTable}},
  {"filter",[]string{"FORWARD","-i",p.Downstream,"-o",p.Tun,"-s",p.Subnet,"-m","conntrack","--ctstate","NEW,ESTABLISHED,RELATED","-m","comment","--comment",tetherMarker,"-j","ACCEPT"}},
  {"filter",[]string{"FORWARD","-i",p.Tun,"-o",p.Downstream,"-d",p.Subnet,"-m","conntrack","--ctstate","ESTABLISHED,RELATED","-m","comment","--comment",tetherMarker,"-j","ACCEPT"}},
  {"nat",[]string{"POSTROUTING","-s",p.Subnet,"-o",p.Tun,"-m","comment","--comment",tetherMarker,"-j","SNAT","--to-source",lease}},
  {"rule",[]string{"pref","9581","to",p.Subnet,"iif",p.Tun,"lookup",tetherTable}},
  {"rule",[]string{"pref","9580","from",p.Subnet,"iif",p.Downstream,"lookup",tetherTable}},
 }
 if p.DNSPort!=0{
  port:=strconv.Itoa(p.DNSPort)
  for _,proto:=range []string{"udp","tcp"}{
   // Explicit destination rather than REDIRECT's interface-first address
   // heuristic. Conntrack performs the original DNS destination inverse.
   out=append(out,tetherCommand{"filter",[]string{"INPUT","-i",p.Downstream,"-s",p.Subnet,
    "-d",p.DNSAddress+"/32","-p",proto,"-m",proto,"--dport",port,
    "-m","conntrack","--ctstate","DNAT","-m","comment","--comment",tetherMarker,"-j","ACCEPT"}})
   out=append(out,tetherCommand{"nat",[]string{"PREROUTING","-i",p.Downstream,"-s",p.Subnet,
    "-p",proto,"-m",proto,"--dport","53","-m","comment","--comment",tetherMarker,
    "-j","DNAT","--to-destination",p.DNSAddress+":"+port}})
  }
 }
 return out
}
type TetherOwner struct{ip,fw Runner;path string;lock *os.File;plan TetherPlan}
func tetherFWKey(words []string)string{
 if len(words)<1||len(words)%2!=1{return ""}
 parts:=[]string{}
 for i:=1;i<len(words);i+=2{
  v:=strings.Trim(words[i+1],"\"")
  if words[i]=="-d"||words[i]=="-s"{if ip,e:=netip.ParseAddr(v);e==nil&&ip.Is4(){v+="/32"}}
  if words[i]=="--ctstate"{a:=strings.Split(v,",");sort.Strings(a);v=strings.Join(a,",")}
  parts=append(parts,words[i]+" "+v)
 }
 sort.Strings(parts)
 return words[0]+" "+strings.Join(parts,"|")
}
// Read only our reserved FIB and marked firewall entries. Refuse unrelated
// occupants; never flush Android's tether chains or any shared route table.
func(s *TetherOwner) state(p TetherPlan)([]bool,error){
 cmds:=p.commands();seen:=make([]bool,len(cmds))
 routes,e:=s.ip("-4","route","show","table","all");if e!=nil{return nil,e}
 for _,line:=range strings.Split(routes,"\n"){
  w:=strings.Fields(line);owned:=false
  for i:=0;i+1<len(w);i++{if w[i]=="table"&&w[i+1]==tetherTable{owned=true}}
  if !owned{continue}
  match:=-1
  for i:=0;i<2;i++{
   a:=cmds[i].args
   if len(w)>=5&&strings.Join(w[:5]," ")==strings.Join(a," "){
    good:=true
    for k:=5;k<len(w);k+=2{
     if k+1>=len(w)||!((w[k]=="scope"&&w[k+1]=="link")||(w[k]=="proto"&&w[k+1]=="boot")){good=false;break}
    }
    if good{match=i}
   }
  }
  if match<0||seen[match]{return nil,fmt.Errorf("foreign tether route")}
  seen[match]=true
 }
 rules,e:=s.ip("-4","rule","show");if e!=nil{return nil,e}
 for _,line:=range strings.Split(rules,"\n"){
  w:=strings.Fields(line);if len(w)==0{continue}
  owned:=w[0]=="9580:"||w[0]=="9581:"
  for i:=0;i+1<len(w);i++{if (w[i]=="lookup"||w[i]=="table")&&w[i+1]==tetherTable{owned=true}}
  if !owned{continue}
  match:=-1
  for i:=5;i<7;i++{
   a:=cmds[i].args
   expected:=append([]string{a[1]+":"},a[2:]...)
   if i==5{expected=append([]string{a[1]+":","from","all"},a[2:]...)}
   if strings.Join(w," ")==strings.Join(expected," "){match=i}
  }
  if match<0||seen[match]{return nil,fmt.Errorf("foreign tether policy rule")}
  seen[match]=true
 }
 for _,pair:=range [][2]string{{"filter","FORWARD"},{"nat","POSTROUTING"},{"filter","INPUT"},{"nat","PREROUTING"}}{
  kind,chain:=pair[0],pair[1]
  out,e:=s.fw("-w","2","-t",kind,"-S",chain);if e!=nil{return nil,e}
  for _,line:=range strings.Split(out,"\n"){
   if !strings.Contains(line,tetherMarker){continue}
   w:=strings.Fields(line);if len(w)<2||w[0]!="-A"{return nil,fmt.Errorf("invalid tether firewall readback")}
   key:=tetherFWKey(w[1:]);match:=-1
   for i,c:=range cmds{if c.kind==kind&&c.args[0]==chain&&key==tetherFWKey(c.args){match=i}}
   if match<0||seen[match]{return nil,fmt.Errorf("foreign tether firewall entry")}
   seen[match]=true
  }
 }
 return seen,nil
}
func(s *TetherOwner) change(c tetherCommand,add bool)error{
 if c.kind=="rule"||c.kind=="route"{
  op:="del";if add{op="add"}
  _,e:=s.ip(append([]string{"-4",c.kind,op},c.args...)...);return e
 }
 op:="-D";a:=append([]string{"-w","2","-t",c.kind,op},c.args...)
 if add{a=append([]string{"-w","2","-t",c.kind,"-I",c.args[0],"1"},c.args[1:]...)}
 _,e:=s.fw(a...);return e
}
func readTether(path string)(TetherPlan,bool,error){
 var p TetherPlan
 f,e:=openNoFollow(path,syscall.O_RDONLY,0);if errors.Is(e,syscall.ENOENT){return p,false,nil}
 if e!=nil{return p,false,e};defer f.Close()
 st,e:=f.Stat();if e!=nil{return p,false,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||owner.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||st.Size()>maxJournalBytes{return p,false,fmt.Errorf("invalid tether journal")}
 d:=json.NewDecoder(io.LimitReader(f,maxJournalBytes+1));d.DisallowUnknownFields()
 if d.Decode(&p)!=nil||!p.valid()||d.Decode(&struct{}{})!=io.EOF{return p,false,fmt.Errorf("invalid tether record")}
 return p,true,nil
}
func writeTether(path string,p TetherPlan)error{
 b,e:=json.Marshal(p);if e!=nil{return e}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600);if e!=nil{return e}
 n,e:=f.Write(b);if e==nil&&n!=len(b){e=io.ErrShortWrite};if e==nil{e=f.Sync()}
 if e=errors.Join(e,f.Close());e!=nil{return e};return parentSync(path)
}
func(s *TetherOwner) remove(p TetherPlan)error{
 seen,e:=s.state(p);if e!=nil{return e}
 cmds:=p.commands()
 for i:=len(cmds)-1;i>=0;i--{if seen[i]{if e=s.change(cmds[i],false);e!=nil{return e}}}
 seen,e=s.state(p);if e!=nil{return e}
 for _,v:=range seen{if v{return fmt.Errorf("tether Stop readback incomplete")}}
 if e=os.Remove(s.path);e!=nil{return e};return parentSync(s.path)
}
func RecoverTether(ip,fw Runner,path string)error{
 l,e:=scopedOwnerLock(path,tetherJournal,"tether-owner.lock");if e!=nil{return e};defer l.Close()
 p,found,e:=readTether(path);if e!=nil||!found{return e}
 return (&TetherOwner{ip:ip,fw:fw,path:path}).remove(p)
}
func NewTether(ip,fw Runner,path string,p TetherPlan)(*TetherOwner,error){
 p.Version=1
 if ip==nil||fw==nil||!p.valid(){return nil,fmt.Errorf("invalid tether scope")}
 l,e:=scopedOwnerLock(path,tetherJournal,"tether-owner.lock");if e!=nil{return nil,e}
 s:=&TetherOwner{ip:ip,fw:fw,path:path,lock:l,plan:p}
 fail:=func(e error)(*TetherOwner,error){l.Close();return nil,e}
 old,found,e:=readTether(path);if e!=nil{return fail(e)}
 if found{if e=s.remove(old);e!=nil{return fail(e)}}
 seen,e:=s.state(p);if e!=nil{return fail(e)}
 for _,v:=range seen{if v{return fail(fmt.Errorf("tether kernel state without journal"))}}
 if e=writeTether(path,p);e!=nil{return fail(e)}
 for _,c:=range p.commands(){if e=s.change(c,true);e!=nil{return fail(errors.Join(e,s.remove(p)))}}
 seen,e=s.state(p);if e!=nil{return fail(errors.Join(e,s.remove(p)))}
 for _,v:=range seen{if !v{return fail(errors.Join(fmt.Errorf("tether readback incomplete"),s.remove(p)))}}
 return s,nil
}
func(s *TetherOwner) Stop()error{
 if s.lock==nil{return nil}
 e:=s.remove(s.plan);e=errors.Join(e,s.lock.Close());s.lock=nil;return e
}
