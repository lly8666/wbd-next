package rootjournal

import (
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/netip"
 "os"
 "path/filepath"
 "strconv"
 "strings"
 "syscall"
)

// B70: Linux kernel SIT (IPv6-in-IPv4) over the existing authenticated
// IPv4 business path. Server 6rd extracts the low 16 bits of the original
// /32 lease. Native IPv6 M3 wire format is NOT changed.
const IPv6CarrierPrefix="fd65:5742:7636::/48"
const ipv6CarrierIface="wbd_sit0"
const ipv6CarrierTable="19847"
const ipv6CarrierMarker="wbd-next-ipv6-carrier-v1"
const ipv6CarrierJournal="ipv6-carrier-journal.json"
const ipv6OuterPref=9598
const ipv6ProofPref=9597
const ipv6TetherPref=9580
const ipv6UIDPref=9600

type IPv6Plan struct{
 Version int
 Server bool
 Tun,Local4,Gateway4,Egress string
 MTU int
 All bool
 UIDs,ExcludedAppIDs []int
 // Optional real existing Android downstream global IPv6 /64 addresses.
 Downstream string
 Downstream6 []string
 DirectCIDRs []string `json:",omitempty"`
}
// Direct prefixes fall through to Android's later routing policy; they never
// create a second packet path. Keep the carrier address space on its SIT link.
func ParseIPv6DirectCIDRs(raw string)([]string,error){
 if strings.TrimSpace(raw)==""{return nil,nil}
 items:=strings.Split(raw,",")
 if len(items)>16{return nil,fmt.Errorf("at most 16 IPv6 direct CIDRs")}
 return mergeIPv6DirectCIDRs(nil,items)
}
func mergeIPv6DirectCIDRs(a,b []string)([]string,error){
 var out []string
 seen:=map[netip.Prefix]bool{}
 carrier:=netip.MustParsePrefix(IPv6CarrierPrefix)
 for _,items:=range [][]string{a,b}{
  for _,raw:=range items{
   p,e:=netip.ParsePrefix(strings.TrimSpace(raw))
   if e!=nil||!p.Addr().Is6()||p.Addr().Is4In6()||p.Bits()==0||carrier.Overlaps(p){return nil,fmt.Errorf("invalid IPv6 direct CIDR %q",raw)}
   p=p.Masked()
   if !seen[p]{seen[p]=true;out=append(out,p.String())}
  }
 }
 if len(out)>32{return nil,fmt.Errorf("too many IPv6 direct CIDRs")}
 return out,nil
}
// Merge current physical interface prefixes with explicit settings at each
// cold connection, so switching Network never reuses the old LAN routes.
func IPv6DirectLAN(manual []string,addrs []string)([]string,error){
 lan:=[]string{"fe80::/10","ff00::/8"}
 carrier:=netip.MustParsePrefix(IPv6CarrierPrefix)
 for _,raw:=range addrs{
  p,e:=netip.ParsePrefix(raw)
  if e!=nil||!p.Addr().Is6()||p.Addr().Is4In6()||!p.Addr().IsGlobalUnicast()||p.Bits()==128||carrier.Overlaps(p){continue}
  lan=append(lan,p.Masked().String())
 }
 return mergeIPv6DirectCIDRs(manual,lan)
}
func IPv6LeaseAddress(ip netip.Addr)netip.Addr{
 if !ip.Is4(){return netip.Addr{}}
 a:=netip.MustParsePrefix(IPv6CarrierPrefix).Addr().As16()
 v:=ip.As4()
 a[6],a[7],a[15]=v[2],v[3],1
 return netip.AddrFrom16(a)
}
func(p IPv6Plan) relay()netip.Prefix{
 a,e:=netip.ParseAddr(p.Gateway4);if e!=nil||!a.Is4(){return netip.Prefix{}}
 return netip.PrefixFrom(a,16).Masked()
}
func(p IPv6Plan) local6()string{return IPv6LeaseAddress(netip.MustParseAddr(p.Local4)).String()}
func(p IPv6Plan) gateway6()string{return IPv6LeaseAddress(netip.MustParseAddr(p.Gateway4)).String()}
func(p IPv6Plan) remote4()string{if p.Server{return "any"};return p.Gateway4}
func(p IPv6Plan) ranges()[]allRange{
 if p.All{return (AllAppPlan{ExcludedAppIDs:p.ExcludedAppIDs}).ranges()}
 out:=make([]allRange,0,len(p.UIDs))
 for _,uid:=range p.UIDs{out=append(out,allRange{uid,uid})}
 return out
}
func(p IPv6Plan) valid()bool{
 local,e:=netip.ParseAddr(p.Local4);peer,f:=netip.ParseAddr(p.Gateway4)
 if p.Version!=1||!nameOK(p.Tun)||p.Tun==ipv6CarrierIface||
    e!=nil||f!=nil||!local.Is4()||!peer.Is4()||!local.IsPrivate()||!peer.IsPrivate()||
    !p.relay().Contains(local)||p.MTU<1280||p.MTU>1480{return false}
 if p.Server{return local==peer&&nameOK(p.Egress)&&p.Egress!=p.Tun&&p.Egress!=ipv6CarrierIface&&!p.All&&len(p.UIDs)==0&&len(p.ExcludedAppIDs)==0&&p.Downstream==""&&len(p.Downstream6)==0&&len(p.DirectCIDRs)==0}
 if local==peer||p.Egress!=""{return false}
 direct,e:=mergeIPv6DirectCIDRs(nil,p.DirectCIDRs)
 if e!=nil||strings.Join(direct,",")!=strings.Join(p.DirectCIDRs,","){return false}
 if (p.Downstream=="")!=(len(p.Downstream6)==0)||len(p.Downstream6)>4{return false}
 if p.Downstream!=""{
  if !nameOK(p.Downstream)||p.Downstream==p.Tun||p.Downstream==ipv6CarrierIface{return false}
  seen:=map[netip.Prefix]bool{}
  for _,raw:=range p.Downstream6{
   q,e:=netip.ParsePrefix(raw)
   if e!=nil||q.Bits()!=64||!q.Addr().Is6()||q.Addr().Is4In6()||
      !q.Addr().IsGlobalUnicast()||q.Addr()==q.Masked().Addr()||
      netip.MustParsePrefix(IPv6CarrierPrefix).Overlaps(q)||seen[q.Masked()]{return false}
   seen[q.Masked()]=true
  }
 }
 if p.All{return len(p.UIDs)==0&&ValidAllAppExclusions(p.ExcludedAppIDs)}
 if len(p.ExcludedAppIDs)!=0{return false}
 if len(p.UIDs)==1{return p.UIDs[0]>=10000&&p.UIDs[0]<=1999999}
 return ValidGroupUIDs(p.UIDs)
}
type carrierCmd struct{tool,kind string;args []string}
func(p IPv6Plan) commands()[]carrierCmd{
 var out []carrierCmd
 route:=func(family,dst,dev,src string){
  out=append(out,carrierCmd{"ip",family,[]string{"route",dst,"dev",dev,"src",src,"table",ipv6CarrierTable}})
 }
 rule:=func(family string,priority int,selectors ...string){
  out=append(out,carrierCmd{"ip",family,append(append([]string{"rule","pref",strconv.Itoa(priority)},selectors...),"lookup",ipv6CarrierTable)})
 }
 fw:=func(family,table string,args ...string){out=append(out,carrierCmd{family,table,append(append([]string(nil),args[:len(args)-2]...),append([]string{"-m","comment","--comment",ipv6CarrierMarker},args[len(args)-2:]...)...)})}
 // Insertion at chain head: install the drop first, then the exact
 // allow before it. Outer proto41 can reach SIT only via original TUN.
 fw("fw4","filter","INPUT","-p","41","-d",p.Local4+"/32","-j","DROP")
 src:=p.Gateway4+"/32";if p.Server{src=p.relay().String()}
 fw("fw4","filter","INPUT","-i",p.Tun,"-p","41","-s",src,"-d",p.Local4+"/32","-j","ACCEPT")
 if p.Server{
  fw("fw6","filter","INPUT","-i",ipv6CarrierIface,"-j","DROP")
  fw("fw6","filter","INPUT","-i",ipv6CarrierIface,"-p","ipv6-icmp","-s",IPv6CarrierPrefix,"-d",p.local6()+"/128","-j","ACCEPT")
  fw("fw6","filter","FORWARD","-i",ipv6CarrierIface,"-j","DROP")
  fw("fw6","filter","FORWARD","-o",ipv6CarrierIface,"-j","DROP")
  fw("fw6","filter","FORWARD","-i",ipv6CarrierIface,"-o",p.Egress,"-s",IPv6CarrierPrefix,"-m","conntrack","--ctstate","NEW,ESTABLISHED,RELATED","-j","ACCEPT")
  fw("fw6","filter","FORWARD","-i",p.Egress,"-o",ipv6CarrierIface,"-d",IPv6CarrierPrefix,"-m","conntrack","--ctstate","ESTABLISHED,RELATED","-j","ACCEPT")
  fw("fw6","nat","POSTROUTING","-s",IPv6CarrierPrefix,"-o",p.Egress,"-j","MASQUERADE")
  route("-6",IPv6CarrierPrefix,ipv6CarrierIface,p.local6())
  rule("-6",ipv6UIDPref,"to",IPv6CarrierPrefix)
 }else{
  for _,raw:=range p.Downstream6{
   q:=netip.MustParsePrefix(raw);subnet:=q.Masked().String()
   fw("fw6","filter","FORWARD","-i",p.Downstream,"-o",ipv6CarrierIface,"-s",subnet,"-m","conntrack","--ctstate","NEW,ESTABLISHED,RELATED","-j","ACCEPT")
   fw("fw6","filter","FORWARD","-i",ipv6CarrierIface,"-o",p.Downstream,"-d",subnet,"-m","conntrack","--ctstate","ESTABLISHED,RELATED","-j","ACCEPT")
   fw("fw6","nat","POSTROUTING","-s",subnet,"-o",ipv6CarrierIface,"-j","SNAT") // exact source inserted below
   last:=&out[len(out)-1];last.args=append(last.args,"--to-source",p.local6())
  }
  route("-4",p.Gateway4+"/32",p.Tun,p.Local4)
  rule("-4",ipv6OuterPref,"from",p.Local4+"/32","to",p.Gateway4+"/32","ipproto","41")
  route("-6","default",ipv6CarrierIface,p.local6())
  // Downstream return routes must win over an identical direct prefix.
  downstream:=map[string]bool{}
  for _,raw:=range p.Downstream6{downstream[netip.MustParsePrefix(raw).Masked().String()]=true}
  for _,cidr:=range p.DirectCIDRs{
   if !downstream[cidr]{out=append(out,carrierCmd{"ip","-6",[]string{"route","throw",cidr,"table",ipv6CarrierTable}})}
  }
  // Cold, actual peer echo from root. This cannot route other root traffic.
  rule("-6",ipv6ProofPref,"from",p.local6()+"/128","to",p.gateway6()+"/128","uidrange","0-0")
  for i,raw:=range p.Downstream6{
   q:=netip.MustParsePrefix(raw);subnet:=q.Masked().String()
   route("-6",subnet,p.Downstream,q.Addr().String())
   rule("-6",ipv6TetherPref+2*i,"to",subnet,"iif",ipv6CarrierIface)
   rule("-6",ipv6TetherPref+2*i+1,"from",subnet,"iif",p.Downstream)
  }
  for i,r:=range p.ranges(){rule("-6",ipv6UIDPref+i,"uidrange",fmt.Sprintf("%d-%d",r.from,r.to))}
 }
 return out
}
func hasPair(w []string,k,v string)bool{for i:=0;i+1<len(w);i++{if w[i]==k&&w[i+1]==v{return true}};return false}
func carrierIP(s string)string{
 if p,e:=netip.ParsePrefix(s);e==nil{return p.String()}
 if a,e:=netip.ParseAddr(s);e==nil{return netip.PrefixFrom(a,a.BitLen()).String()}
 return s
}
func carrierFWKey(w []string)string{
 w=append([]string(nil),w...)
 for i:=1;i+1<len(w);i+=2{
  if w[i]=="-s"||w[i]=="-d"{w[i+1]=carrierIP(w[i+1])}
  if w[i]=="-p"&&(w[i+1]=="ipv6"||w[i+1]=="41"){w[i+1]="41"}
  if w[i]=="-p"&&w[i+1]=="icmpv6"{w[i+1]="ipv6-icmp"}
 }
 return tetherFWKey(w)
}
func carrierRouteMatch(w,a []string)bool{
 if len(a)==5&&a[1]=="throw"{
  if len(w)<4||w[0]!="throw"||carrierIP(w[1])!=carrierIP(a[2])||!hasPair(w,"table",ipv6CarrierTable){return false}
  for i:=2;i<len(w);i+=2{
   if i+1>=len(w){return false}
   switch w[i]{
   case "table":if w[i+1]!=ipv6CarrierTable{return false}
   case "proto":if w[i+1]!="boot"&&w[i+1]!="static"{return false}
   case "metric":if w[i+1]!="1024"{return false}
   case "pref":if w[i+1]!="medium"{return false}
   default:return false
   }
  }
  return true
 }
 if len(w)<5||len(a)!=8||carrierIP(w[0])!=carrierIP(a[1])||
    !hasPair(w,"dev",a[3])||!hasPair(w,"src",a[5])||!hasPair(w,"table",ipv6CarrierTable){return false}
 for i:=1;i<len(w);i+=2{
  if i+1>=len(w){return false}
  switch w[i]{
  case "dev","src","table": // checked above
  case "scope":if w[i+1]!="link"{return false}
  case "proto":if w[i+1]!="boot"&&w[i+1]!="static"{return false}
  case "metric":if w[i+1]!="1024"{return false}
  case "pref":if w[i+1]!="medium"{return false}
  default:return false
  }
 }
 return true
}
func carrierRuleMatch(w,a []string)bool{
 if len(w)<3||w[0]!=a[2]+":"{return false}
 expected:=map[string]string{"from":"all"}
 for i:=3;i+1<len(a);i+=2{expected[a[i]]=a[i+1]}
 got:=map[string]string{}
 for i:=1;i+1<len(w);i+=2{
  k,v:=w[i],w[i+1];if k=="table"{k="lookup"}
  if _,ok:=got[k];ok{return false}
  if k=="from"||k=="to"{v=carrierIP(v)}
  if k=="ipproto"&&v=="ipv6"{v="41"}
  got[k]=v
 }
 if len(w)%2!=1||len(got)!=len(expected){return false}
 for k,v:=range expected{if k=="from"||k=="to"{v=carrierIP(v)};if got[k]!=v{return false}}
 return true
}
type carrierState struct{link,addr,ready bool;rows []bool}
type IPv6Owner struct{ip,fw4,fw6 Runner;batchIP func([][]string)error;path string;lock *os.File;plan IPv6Plan}
func(s *IPv6Owner) state(p IPv6Plan)(carrierState,error){
 cmds:=p.commands();x:=carrierState{rows:make([]bool,len(cmds))}
 links,e:=s.ip("-d","-o","link","show");if e!=nil{return x,e}
 for _,line:=range strings.Split(links,"\n"){
  w:=strings.Fields(line)
  if len(w)<2||strings.Split(strings.TrimSuffix(w[1],":"),"@")[0]!=ipv6CarrierIface{continue}
  if x.link||!hasPair(w,"alias",ipv6CarrierMarker)||!hasPair(w,"local",p.Local4)||
    !(hasPair(w,"remote",p.remote4())||p.Server&&hasPair(w,"remote","0.0.0.0")){
   return x,fmt.Errorf("foreign SIT identity")
  }
  // The exact marker and tuple survive partial installation or a dead
  // lower TUN. Readiness (6rd, lower device, MTU) is required to publish,
  // not to remove this exact journal-owned link after a crash.
  x.link=true
  x.ready=hasPair(w,"6rd-prefix",IPv6CarrierPrefix)&&
   hasPair(w,"6rd-relay_prefix",p.relay().String())&&
   hasPair(w,"mtu",strconv.Itoa(p.MTU))&&
   (hasPair(w,"dev",p.Tun)||strings.Contains(w[1],"@"+p.Tun+":"))
 }
 addrs,e:=s.ip("-6","-o","addr","show");if e!=nil{return x,e}
 for _,line:=range strings.Split(addrs,"\n"){
  w:=strings.Fields(line);if len(w)<4||w[2]!="inet6"{continue}
  prefix,err:=netip.ParsePrefix(w[3]);if err!=nil{continue}
  iface:=strings.Split(strings.TrimSuffix(w[1],"\\"),"@")[0]
  if prefix.Addr().String()==p.local6(){
   if x.addr||!x.link||iface!=ipv6CarrierIface||prefix.Bits()!=128{return x,fmt.Errorf("foreign IPv6 lease address")}
   x.addr=true
  }
 }
 for _,family:=range []string{"-4","-6"}{
  for _,kind:=range []string{"route","rule"}{
   args:=[]string{family,kind,"show"};if kind=="route"{args=append(args,"table","all")}
   lines,e:=s.ip(args...);if e!=nil{return x,e}
   for _,line:=range strings.Split(lines,"\n"){
    w:=strings.Fields(line);if len(w)==0{continue}
    owned:=hasPair(w,"table",ipv6CarrierTable)||hasPair(w,"lookup",ipv6CarrierTable)
    if kind=="rule"{
     n,_:=strconv.Atoi(strings.TrimSuffix(w[0],":"))
     if family=="-6"&&(n>=ipv6UIDPref&&n<ipv6UIDPref+AllMaxRules||n==ipv6ProofPref||n>=ipv6TetherPref&&n<ipv6TetherPref+8)||family=="-4"&&n==ipv6OuterPref{owned=true}
    }
    if !owned{continue}
    found:=-1
    for i,c:=range cmds{
     if c.tool!="ip"||c.kind!=family||c.args[0]!=kind{continue}
     ok:=false
     if kind=="rule"{ok=carrierRuleMatch(w,c.args)}else{ok=carrierRouteMatch(w,c.args)}
     if ok{found=i;break}
    }
    if found<0||x.rows[found]{return x,fmt.Errorf("foreign or duplicate SIT FIB state: %s",line)}
    x.rows[found]=true
   }
  }
 }
 for _,pair:=range [][3]string{{"fw4","filter","INPUT"},{"fw6","filter","INPUT"},{"fw6","filter","FORWARD"},{"fw6","nat","POSTROUTING"}}{
  if !p.Server&&len(p.Downstream6)==0&&pair[0]=="fw6"{continue}
  fw:=s.fw4;if pair[0]=="fw6"{fw=s.fw6}
  lines,e:=fw("-w","2","-t",pair[1],"-S",pair[2]);if e!=nil{return x,e}
  for _,line:=range strings.Split(lines,"\n"){
   if !strings.Contains(line,ipv6CarrierMarker){continue}
   w:=strings.Fields(line);if len(w)<2||w[0]!="-A"{return x,fmt.Errorf("foreign SIT firewall entry")}
   found:=-1
   for i,c:=range cmds{if c.tool==pair[0]&&c.kind==pair[1]&&carrierFWKey(c.args)==carrierFWKey(w[1:]){found=i;break}}
   if found<0||x.rows[found]{return x,fmt.Errorf("foreign or duplicate SIT firewall entry")}
   x.rows[found]=true
  }
 }
 return x,nil
}
func(s *IPv6Owner) change(c carrierCmd,add bool)error{
 if c.tool=="ip"{
  op:="del";if add{op="add"}
  _,e:=s.ip(append([]string{c.kind,c.args[0],op},c.args[1:]...)...);return e
 }
 fw:=s.fw4;if c.tool=="fw6"{fw=s.fw6}
 a:=append([]string{"-w","2","-t",c.kind,"-D"},c.args...)
 if add{a=append([]string{"-w","2","-t",c.kind,"-I",c.args[0],"1"},c.args[1:]...)}
 _,e:=fw(a...);return e
}
// One family-specific ip -batch for contiguous cold FIB operations,
// with exact readback and journal rollback on any partially applied batch.
func(s *IPv6Owner) changeAll(cmds []carrierCmd,present []bool,add bool)error{
 var pending [][]string
 flush:=func()error{
  if len(pending)==0{return nil}
  e:=s.batchIP(pending);pending=nil;return e
 }
 for pos:=0;pos<len(cmds);pos++{
  i:=pos;if !add{i=len(cmds)-1-pos}
  if present!=nil&&!present[i]{continue}
  c:=cmds[i]
  if s.batchIP!=nil&&c.tool=="ip"{
   op:="del";if add{op="add"}
   pending=append(pending,append([]string{c.kind,c.args[0],op},c.args[1:]...))
   continue
  }
  if e:=flush();e!=nil{return e}
  if e:=s.change(c,add);e!=nil{return e}
 }
 return flush()
}
func readIPv6Carrier(path string)(IPv6Plan,bool,error){
 var p IPv6Plan
 f,e:=openNoFollow(path,syscall.O_RDONLY,0);if errors.Is(e,syscall.ENOENT){return p,false,nil}
 if e!=nil{return p,false,e};defer f.Close()
 st,e:=f.Stat();if e!=nil{return p,false,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||owner.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||st.Size()>maxJournalBytes{return p,false,fmt.Errorf("invalid SIT journal")}
 d:=json.NewDecoder(io.LimitReader(f,maxJournalBytes+1));d.DisallowUnknownFields()
 if d.Decode(&p)!=nil||!p.valid()||d.Decode(&struct{}{})!=io.EOF{return p,false,fmt.Errorf("invalid SIT scope")}
 return p,true,nil
}
func writeIPv6Carrier(path string,p IPv6Plan)error{
 b,e:=json.Marshal(p);if e!=nil{return e}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600);if e!=nil{return e}
 n,e:=f.Write(b);if e==nil&&n!=len(b){e=io.ErrShortWrite};if e==nil{e=f.Sync()}
 if e=errors.Join(e,f.Close());e!=nil{return e};return parentSync(path)
}
func(s *IPv6Owner) remove(p IPv6Plan)error{
 x,e:=s.state(p);if e!=nil{return e}
 cmds:=p.commands()
 if e=s.changeAll(cmds,x.rows,false);e!=nil{return e}
 if x.link{if _,e=s.ip("link","del","dev",ipv6CarrierIface);e!=nil{return e}}
 x,e=s.state(p);if e!=nil{return e}
 if x.link||x.addr{return fmt.Errorf("SIT Stop retained link/address")}
 for _,v:=range x.rows{if v{return fmt.Errorf("SIT Stop retained FIB/firewall")}}
 if e=os.Remove(s.path);e!=nil{return e};return parentSync(s.path)
}
func RecoverIPv6Carrier(ip,fw4,fw6 Runner,path string)error{
 return RecoverIPv6CarrierBatch(ip,fw4,fw6,nil,path)
}
func RecoverIPv6CarrierBatch(ip,fw4,fw6 Runner,batch func([][]string)error,path string)error{
 l,e:=scopedOwnerLock(path,ipv6CarrierJournal,"ipv6-carrier-owner.lock");if e!=nil{return e};defer l.Close()
 p,found,e:=readIPv6Carrier(path);if e!=nil||!found{return e}
 return (&IPv6Owner{ip:ip,fw4:fw4,fw6:fw6,batchIP:batch,path:path}).remove(p)
}
func NewIPv6Carrier(ip,fw4,fw6 Runner,path string,p IPv6Plan)(*IPv6Owner,error){
 return NewIPv6CarrierBatch(ip,fw4,fw6,nil,path,p)
}
func NewIPv6CarrierBatch(ip,fw4,fw6 Runner,batch func([][]string)error,path string,p IPv6Plan)(*IPv6Owner,error){
 p.Version=1
 if ip==nil||fw4==nil||fw6==nil||!p.valid()||filepath.Base(path)!=ipv6CarrierJournal{return nil,fmt.Errorf("invalid IPv6 carrier scope")}
 l,e:=scopedOwnerLock(path,ipv6CarrierJournal,"ipv6-carrier-owner.lock");if e!=nil{return nil,e}
 s:=&IPv6Owner{ip:ip,fw4:fw4,fw6:fw6,batchIP:batch,path:path,plan:p,lock:l}
 fail:=func(e error)(*IPv6Owner,error){l.Close();return nil,e}
 old,found,e:=readIPv6Carrier(path);if e!=nil{return fail(e)}
 if found{if e=s.remove(old);e!=nil{return fail(e)}}
 x,e:=s.state(p);if e!=nil{return fail(e)}
 if x.link||x.addr{return fail(fmt.Errorf("unowned SIT link"))}
 for _,v:=range x.rows{if v{return fail(fmt.Errorf("unowned SIT rule"))}}
 if e=writeIPv6Carrier(path,p);e!=nil{return fail(e)}
 rollback:=func(e error)(*IPv6Owner,error){return fail(errors.Join(e,s.remove(p)))}
 if _,e=ip("link","add","name",ipv6CarrierIface,"alias",ipv6CarrierMarker,"type","sit",
   "local",p.Local4,"remote",p.remote4(),"dev",p.Tun,"ttl","inherit","nopmtudisc",
   "6rd-prefix",IPv6CarrierPrefix,"6rd-relay_prefix",p.relay().String());e!=nil{return rollback(e)}
 if _,e=ip("link","set","dev",ipv6CarrierIface,"mtu",strconv.Itoa(p.MTU),"up");e!=nil{return rollback(e)}
 if _,e=ip("-6","addr","add",p.local6()+"/128","dev",ipv6CarrierIface,"nodad","noprefixroute");e!=nil{return rollback(e)}
 if e=s.changeAll(p.commands(),nil,true);e!=nil{return rollback(e)}
 x,e=s.state(p);if e!=nil||!x.link||!x.ready||!x.addr{return rollback(errors.Join(e,fmt.Errorf("SIT link/address readback incomplete")))}
 for _,v:=range x.rows{if !v{return rollback(fmt.Errorf("SIT FIB/firewall readback incomplete"))}}
 return s,nil
}
func(s *IPv6Owner) Stop()error{
 if s.lock==nil{return nil}
 e:=s.remove(s.plan);e=errors.Join(e,s.lock.Close());s.lock=nil;return e
}
