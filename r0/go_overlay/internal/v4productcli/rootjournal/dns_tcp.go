package rootjournal

import (
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/netip"
 "os"
 "path/filepath"
 "sort"
 "strconv"
 "strings"
 "syscall"
)

const dnsTable="19843"
const dnsPriority="9599"
const dnsMarker="wbd-next-root-app-tcp-dns-v1"
const dnsJournalName="dns-tcp-journal.json"
const dnsUpstream="1.1.1.1/32"

// Same selected ordinary UID set as the authenticated original UID FIB.
// Tunnel is required for tunnel or CN-split mode, never for physical-only.
type DNSPlan struct{
 Version int
 Tun,Lease string
 Port int
 Tunnel,All bool
 TunnelUpstream string `json:",omitempty"`
 // Tether DNS can own the original root-to-tunnel route without
 // changing ordinary application TCP53 policy. Old journal defaults false.
 NoAppNAT bool
 UIDs,ExcludedAppIDs []int
}
func(p DNSPlan) upstream()string{if p.TunnelUpstream==""{return dnsUpstream};return p.TunnelUpstream+"/32"}
func(p DNSPlan) ranges()[]allRange{
 if p.All{return (AllAppPlan{ExcludedAppIDs:p.ExcludedAppIDs}).ranges()}
 out:=make([]allRange,0,len(p.UIDs))
 for _,uid:=range p.UIDs{out=append(out,allRange{uid,uid})}
 return out
}
func(p DNSPlan) valid()bool{
 lease,e:=netip.ParsePrefix(p.Lease)
 if p.TunnelUpstream!=""{a,err:=netip.ParseAddr(p.TunnelUpstream);if err!=nil||!a.Is4()||a.IsUnspecified()||a.IsLoopback()||a.IsMulticast()||a.IsLinkLocalUnicast()||a.As4()[0]>=224||a.String()!=p.TunnelUpstream{return false}}
 if p.Version!=1||!nameOK(p.Tun)||p.Port<1||p.Port>65535||
  e!=nil||lease.Bits()!=32||!lease.Addr().Is4()||lease.Addr().IsUnspecified()||
  lease.Addr().IsMulticast(){return false}
 if p.All{return len(p.UIDs)==0&&ValidAllAppExclusions(p.ExcludedAppIDs)}
 if len(p.ExcludedAppIDs)!=0||len(p.UIDs)==0{return false}
 if len(p.UIDs)==1{return p.UIDs[0]>=10000&&p.UIDs[0]<=1999999}
 return ValidGroupUIDs(p.UIDs)
}
func(p DNSPlan) appRanges()[]allRange{
 if p.NoAppNAT{return nil}
 return p.ranges()
}
func dnsRoute(p DNSPlan,action string)[]string{
 return []string{"-4","route",action,p.upstream(),"dev",p.Tun,"table",dnsTable}
}
func dnsRule(p DNSPlan,action string)[]string{
 return []string{"-4","rule",action,"pref",dnsPriority,"from",p.Lease,
  "to",p.upstream(),"uidrange","0-0","lookup",dnsTable}
}
func dnsNAT(p DNSPlan,r allRange,action string)[]string{
 uid:=strconv.Itoa(r.from)
 if r.from!=r.to{uid+="-"+strconv.Itoa(r.to)}
 return []string{action,"OUTPUT","-o",p.Tun,"-p","tcp","-m","tcp",
  "--dport","53","-m","owner","--uid-owner",uid,
  "-m","comment","--comment",dnsMarker,"-j","REDIRECT","--to-ports",strconv.Itoa(p.Port)}
}
// iptables -S prints canonical option order; compare exact option/value
// pairs without relying on the order or quoted comment representation.
func dnsNATKey(words []string)(string,error){
 if len(words)%2!=0||len(words)<2||words[0]!="-A"||words[1]!="OUTPUT"{
  return "",fmt.Errorf("unexpected owned DNS NAT rule")
 }
 var pairs []string
 for i:=2;i<len(words);i+=2{
  key,value:=words[i],strings.Trim(words[i+1],"\"")
  if key=="--uid-owner"||key=="--to-ports"{
   parts:=strings.Split(value,"-")
   if len(parts)==2&&parts[0]==parts[1]{value=parts[0]}
  }
  pairs=append(pairs,key+" "+value)
 }
 sort.Strings(pairs);return strings.Join(pairs,"|"),nil
}
type DNSOwner struct{
 ip,firewall Runner
 batch func([][]string)error
 path string
 lock *os.File
 plan DNSPlan
}
func dnsLock(path string)(*os.File,error){
 return scopedOwnerLock(path,dnsJournalName,"dns-tcp-owner.lock")
}
func scopedOwnerLock(path,journalName,lockName string)(*os.File,error){
 if filepath.Base(path)!=journalName{return nil,fmt.Errorf("invalid scoped journal path")}
 if e:=ownedDirectory(filepath.Join(filepath.Dir(path),"route-journal.json"));e!=nil{return nil,e}
 f,e:=openNoFollow(filepath.Join(filepath.Dir(path),lockName),
  syscall.O_RDWR|syscall.O_CREAT,0600)
 if e!=nil{return nil,e}
 st,e:=f.Stat()
 if e!=nil{f.Close();return nil,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||owner.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||st.Mode().Perm()!=0600{
  f.Close();return nil,fmt.Errorf("foreign DNS owner lock")
 }
 if e=syscall.Flock(int(f.Fd()),syscall.LOCK_EX|syscall.LOCK_NB);e!=nil{f.Close();return nil,e}
 return f,nil
}
func readDNS(path string)(DNSPlan,bool,error){
 var p DNSPlan
 f,e:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(e,syscall.ENOENT){return p,false,nil}
 if e!=nil{return p,false,e};defer f.Close()
 st,e:=f.Stat();if e!=nil{return p,false,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||owner.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||
  st.Mode().Perm()!=0600||st.Size()<2||st.Size()>maxJournalBytes{
  return p,false,fmt.Errorf("invalid DNS journal")
 }
 dec:=json.NewDecoder(io.LimitReader(f,maxJournalBytes+1))
 dec.DisallowUnknownFields()
 if dec.Decode(&p)!=nil||!p.valid()||dec.Decode(&struct{}{})!=io.EOF{
  return p,false,fmt.Errorf("invalid DNS owner record")
 }
 return p,true,nil
}
func writeDNS(path string,p DNSPlan)error{
 b,e:=json.Marshal(p);if e!=nil{return e}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
 if e!=nil{return e}
 n,e:=f.Write(b);if e==nil&&n!=len(b){e=io.ErrShortWrite}
 if e==nil{e=f.Sync()};e=errors.Join(e,f.Close())
 if e!=nil{return e}
 return parentSync(path)
}
type dnsState struct{route,rule bool;nat [][]string}
func(s *DNSOwner) state(p DNSPlan)(dnsState,error){
 var state dnsState
 // table all avoids ENOENT from ip route show on a not-yet-created table.
 routes,e:=s.ip("-4","route","show","table","all");if e!=nil{return state,e}
 for _,line:=range strings.Split(routes,"\n"){
  w:=strings.Fields(line);at:=-1
  for i:=0;i+1<len(w);i++{if w[i]=="table"&&w[i+1]==dnsTable{at=i;break}}
  if at<0{continue}
  if state.route||!p.Tunnel||at!=3||len(w)<5||
   strings.TrimSuffix(w[0],"/32")!=strings.TrimSuffix(p.upstream(),"/32")||w[1]!="dev"||w[2]!=p.Tun{
   return state,fmt.Errorf("foreign DNS upstream route")
  }
  for i:=5;i<len(w);i+=2{
   if i+1>=len(w)||!((w[i]=="scope"&&w[i+1]=="link")||
      (w[i]=="proto"&&w[i+1]=="boot")){return state,fmt.Errorf("foreign DNS route attributes")}
  }
  state.route=true
 }
 rules,e:=s.ip("-4","rule","show");if e!=nil{return state,e}
 for _,line:=range strings.Split(rules,"\n"){
  w:=strings.Fields(line);if len(w)==0{continue}
  owns:=w[0]==dnsPriority+":"
  for i:=0;i+1<len(w);i++{
   if (w[i]=="lookup"||w[i]=="table")&&w[i+1]==dnsTable{owns=true}
  }
  if !owns{continue}
  if state.rule||!p.Tunnel||len(w)!=9||w[0]!=dnsPriority+":"||
   w[1]!="from"||strings.TrimSuffix(w[2],"/32")!=strings.TrimSuffix(p.Lease,"/32")||
   w[3]!="to"||strings.TrimSuffix(w[4],"/32")!=strings.TrimSuffix(p.upstream(),"/32")||
   w[5]!="uidrange"||w[6]!="0-0"||
   (w[7]!="lookup"&&w[7]!="table")||w[8]!=dnsTable{
   return state,fmt.Errorf("foreign DNS source policy rule")
  }
  state.rule=true
 }
 expected:=make(map[string][]string)
 for _,r:=range p.appRanges(){
  row:=dnsNAT(p,r,"-A");key,_:=dnsNATKey(row);expected[key]=row
 }
 lines,e:=s.firewall("-w","2","-t","nat","-S","OUTPUT");if e!=nil{return state,e}
 for _,line:=range strings.Split(lines,"\n"){
  if !strings.Contains(line,dnsMarker){continue}
  key,e:=dnsNATKey(strings.Fields(line));if e!=nil{return state,e}
  row,ok:=expected[key];if !ok{return state,fmt.Errorf("foreign or duplicate DNS NAT rule")}
  delete(expected,key);state.nat=append(state.nat,row)
 }
 return state,nil
}
func(s *DNSOwner) changeNAT(rows [][]string,action string)error{
 if len(rows)==0{return nil}
 commands:=make([][]string,0,len(rows))
 for _,row:=range rows{
  cmd:=append([]string(nil),row...);cmd[0]=action;commands=append(commands,cmd)
 }
 if s.batch!=nil{return s.batch(commands)}
 for _,cmd:=range commands{
  if _,e:=s.firewall(append([]string{"-w","2","-t","nat"},cmd...)...);e!=nil{return e}
 }
 return nil
}
func(s *DNSOwner) remove(p DNSPlan)error{
 state,e:=s.state(p);if e!=nil{return e}
 if e=s.changeNAT(state.nat,"-D");e!=nil{return e}
 if state.rule{if _,e=s.ip(dnsRule(p,"del")...);e!=nil{return e}}
 if state.route{if _,e=s.ip(dnsRoute(p,"del")...);e!=nil{return e}}
 state,e=s.state(p)
 if e!=nil{return e}
 if state.route||state.rule||len(state.nat)!=0{return fmt.Errorf("DNS Stop readback incomplete")}
 if e=os.Remove(s.path);e!=nil{return e}
 return parentSync(s.path)
}
// Called by real Root Restore and before the next authorized cold START.
// An absent journal leaves all unrelated NAT and policy state untouched.
func RecoverDNS(ip,fw Runner,batch func([][]string)error,path string)error{
 lock,e:=dnsLock(path);if e!=nil{return e};defer lock.Close()
 old,found,e:=readDNS(path);if e!=nil||!found{return e}
 return (&DNSOwner{ip:ip,firewall:fw,batch:batch,path:path}).remove(old)
}
func NewDNS(ip,fw Runner,batch func([][]string)error,path string,p DNSPlan)(*DNSOwner,error){
 p.Version=1
 if ip==nil||fw==nil||!p.valid(){return nil,fmt.Errorf("invalid original DNS scope")}
 lock,e:=dnsLock(path);if e!=nil{return nil,e}
 s:=&DNSOwner{ip:ip,firewall:fw,batch:batch,path:path,lock:lock,plan:p}
 fail:=func(e error)(*DNSOwner,error){lock.Close();return nil,e}
 old,found,e:=readDNS(path);if e!=nil{return fail(e)}
 if found{if e=s.remove(old);e!=nil{return fail(e)}}
 state,e:=s.state(p)
 if e!=nil{return fail(e)}
 if state.route||state.rule||len(state.nat)!=0{return fail(fmt.Errorf("DNS kernel state without journal"))}
 if e=writeDNS(path,p);e!=nil{return fail(e)}
 rollback:=func(err error)(*DNSOwner,error){return fail(errors.Join(err,s.remove(p)))}
 if p.Tunnel{
  if _,e=ip(dnsRoute(p,"add")...);e!=nil{return rollback(e)}
  if _,e=ip(dnsRule(p,"add")...);e!=nil{return rollback(e)}
 }
 var rows [][]string
 for _,r:=range p.appRanges(){rows=append(rows,dnsNAT(p,r,"-A"))}
 if e=s.changeNAT(rows,"-A");e!=nil{return rollback(e)}
 state,e=s.state(p)
 if e!=nil||state.route!=p.Tunnel||state.rule!=p.Tunnel||len(state.nat)!=len(rows){
  return rollback(errors.Join(e,fmt.Errorf("DNS route/NAT readback incomplete")))
 }
 return s,nil
}
func(s *DNSOwner) Stop()error{
 if s.lock==nil{return nil}
 e:=s.remove(s.plan);e=errors.Join(e,s.lock.Close());s.lock=nil;return e
}
