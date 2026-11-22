package rootjournal

// All ordinary Android application UIDs (20 per-user profiles, app IDs
// 10000..19999), minus fixed, verified app IDs. It is NOT a device-wide
// default route and never includes root, Android system AIDs, or isolated
// processes. One original authenticated /32, one dedicated TUN/table.
// Every kernel mutation is journal-first, exact-readback, owned Stop.
import (
 "crypto/rand"
 "encoding/hex"
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

const (
 allAppsVersion = 4
 legacyAllAppsVersion = 3
 AllAppIDMin = 10000
 AllAppIDMax = 19999
 allPerUserRange = 100000
 allMaxUserProfiles = 20
 AllMaxExcludedAppIDs = 8
 AllMaxRules = allMaxUserProfiles * (AllMaxExcludedAppIDs+1)
)
type AllAppPlan struct {
 Version int `json:"version"`
 ExcludedAppIDs []int `json:"excluded_app_ids"`
 Tun string `json:"tun"`
 Lease string `json:"lease"`
 ServerIP string `json:"server_ip,omitempty"`
 DirectCIDRs []string `json:"direct_cidrs,omitempty"`
 Underlay string `json:"underlay"`
 NetworkHandle uint64 `json:"network_handle"`
 IfIndex int `json:"ifindex"`
 Nonce string `json:"nonce"`
}
type allRange struct{ from,to int }
type AllAppSession struct {
 run Runner
 journal string
 plan AllAppPlan
 lock *os.File
 active bool
}
func ValidAllAppExclusions(a []int) bool {
 // Own WBD app ID and installed KernelSU Manager app ID are BOTH required.
 if len(a)<2||len(a)>AllMaxExcludedAppIDs{return false}
 prev:=0
 for _,id:=range a {
  if id<AllAppIDMin||id>AllAppIDMax||id<=prev{return false}
  prev=id
 }
 return true
}
func validServerPeerIPv4(raw string)bool{
 a,e:=netip.ParseAddr(raw)
 return e==nil&&a.Is4()&&!a.IsUnspecified()&&!a.IsMulticast()&&
  !a.IsLoopback()&&!a.IsLinkLocalUnicast()&&a.String()==raw
}
func (p AllAppPlan) valid()bool{
 lease,e:=netip.ParsePrefix(p.Lease)
 isCurrent:=p.Version==allAppsVersion&&validServerPeerIPv4(p.ServerIP)
 isLegacy:=p.Version==legacyAllAppsVersion&&p.ServerIP==""
 return (isCurrent||isLegacy)&&ValidAllAppExclusions(p.ExcludedAppIDs)&&
  e==nil&&lease.IsValid()&&lease.Bits()==32&&lease.Addr().Is4()&&
  !lease.Addr().IsMulticast()&&!lease.Addr().IsUnspecified()&&
  p.ServerIP!=lease.Addr().String()&&
  validDirectCIDRs(p.DirectCIDRs,p.ServerIP)&&
  nameOK(p.Tun)&&nameOK(p.Underlay)&&p.Tun!=p.Underlay&&
  p.NetworkHandle!=0&&p.IfIndex>0&&len(p.Nonce)==32
}
func peerThrowArgs(action,peer string)[]string{
 return []string{"-4","route",action,"throw",peer+"/32","table",strconv.Itoa(Table)}
}
// Only WBD's private table is edited. Throw /32 keeps app packets to the
// server out of WBD TUN, falling through to Android's later netd rules.
// It does not prove Android's eventual physical-route selection.
func allAppRouteState(out,tun,peer string)(defaultRoute,peerThrow bool,err error){
 for _,line:=range strings.Split(strings.TrimSpace(out),"\n"){
  w:=strings.Fields(line)
  if len(w)==0{continue}
  if w[0]=="default"&&!defaultRoute{
   ok,e:=routeState(line,tun)
   if e!=nil||!ok{return false,false,fmt.Errorf("foreign default route: %w",e)}
   defaultRoute=true;continue
  }
  if w[0]=="throw"&&peer!=""&&!peerThrow{
   if len(w)<2||(w[1]!=peer&&w[1]!=peer+"/32"){
    return false,false,fmt.Errorf("foreign server throw destination")
   }
   scope,proto:=false,false
   for i:=2;i<len(w);i+=2{
    if i+1>=len(w){return false,false,fmt.Errorf("foreign server throw attribute")}
    switch{
    case w[i]=="scope"&&w[i+1]=="link"&&!scope:scope=true
    case w[i]=="proto"&&w[i+1]=="boot"&&!proto:proto=true
    default:return false,false,fmt.Errorf("foreign server throw attribute")
    }
   }
   peerThrow=true;continue
  }
  return false,false,fmt.Errorf("foreign WBD private route")
 }
 return defaultRoute,peerThrow,nil
}
func (p AllAppPlan) ranges()[]allRange{
 result:=make([]allRange,0,AllMaxRules)
 for user:=0;user<allMaxUserProfiles;user++{
  base:=user*allPerUserRange
  cursor:=base+AllAppIDMin
  for _,excluded:=range p.ExcludedAppIDs{
   at:=base+excluded
   if cursor<at{result=append(result,allRange{cursor,at-1})}
   cursor=at+1
  }
  if cursor<=base+AllAppIDMax{
   result=append(result,allRange{cursor,base+AllAppIDMax})
  }
 }
 return result
}
func allRuleArgs(action string,r allRange,index int)[]string{
 return []string{"-4","rule",action,"pref",strconv.Itoa(Priority+index),
  "uidrange",fmt.Sprintf("%d-%d",r.from,r.to),"lookup",strconv.Itoa(Table)}
}
func strictAllRule(fields []string,priority int,r allRange)bool{
 if len(fields)<7||fields[0]!=strconv.Itoa(priority)+":"{return false}
 i:=1
 if fields[i]!="from"||fields[i+1]!="all"{return false}
 i+=2
 if i<len(fields)&&fields[i]=="to"{
  if i+1>=len(fields)||fields[i+1]!="all"{return false}
  i+=2
 }
 if i+3>=len(fields)||fields[i]!="uidrange"||
    fields[i+1]!=fmt.Sprintf("%d-%d",r.from,r.to){return false}
 i+=2
 if (fields[i]!="lookup"&&fields[i]!="table")||
    fields[i+1]!=strconv.Itoa(Table){return false}
 return i+2==len(fields)
}
func allRuleState(out string,rs []allRange)([]bool,error){
 present:=make([]bool,len(rs))
 for _,line:=range strings.Split(out,"\n"){
  w:=strings.Fields(line)
  if len(w)==0{continue}
  priority,e:=strconv.Atoi(strings.TrimSuffix(w[0],":"))
  if e!=nil{return nil,fmt.Errorf("invalid Android ip rule priority")}
  usesOwnedTable:=false
  for i:=1;i+1<len(w);i++{
   if (w[i]=="lookup"||w[i]=="table")&&w[i+1]==strconv.Itoa(Table){
    usesOwnedTable=true
   }
  }
  offset:=priority-Priority
  reserved:=offset>=0&&offset<len(rs)
  if !reserved&&!usesOwnedTable{continue}
  if !reserved||!usesOwnedTable||present[offset]||
    !strictAllRule(w,priority,rs[offset]){
   return nil,fmt.Errorf("foreign or duplicate Android all-app UID rule")
  }
  present[offset]=true
 }
 return present,nil
}
func (s *AllAppSession) query(p AllAppPlan)(bool,bool,[]bool,[]bool,error){
 t,e:=s.run(routeShow()...);if e!=nil{return false,false,nil,nil,e}
 route,peer,direct,e:=routeWithDirect(t,p.Tun,p.ServerIP,p.DirectCIDRs)
 if e!=nil{return false,false,nil,nil,e}
 rules,e:=s.run(ruleShow()...);if e!=nil{return false,false,nil,nil,e}
 present,e:=allRuleState(rules,p.ranges())
 return route,peer,direct,present,e
}
func (s *AllAppSession) requireEmpty(p AllAppPlan)error{
 route,peer,direct,rules,e:=s.query(p)
 if e!=nil{return e}
 if route||peer||anyDirectPresent(direct)||anyRules(rules){
  return fmt.Errorf("all-app private table/rules occupied")
 }
 return nil
}
func (s *AllAppSession) requireReady(p AllAppPlan)error{
 route,peer,direct,rules,e:=s.query(p)
 if e!=nil{return e}
 if !route||(p.Version==allAppsVersion&&!peer)||
  !allDirectPresent(direct)||!allRules(rules){
  return fmt.Errorf("all-app UID/direct/peer exception readback mismatch")
 }
 return nil
}
func (s *AllAppSession) removeExact(p AllAppPlan)error{
 route,peer,direct,rules,e:=s.query(p)
 if e!=nil{return e}
 rs:=p.ranges()
 for i:=len(rules)-1;i>=0;i--{
  if rules[i]{
   if _,e=s.run(allRuleArgs("del",rs[i],i)...);e!=nil{return e}
  }
 }
 for i:=len(direct)-1;i>=0;i--{
  if direct[i]{
   if _,e=s.run(directArgs("del",p.DirectCIDRs[i])...);e!=nil{return e}
  }
 }
 if peer{
  if _,e=s.run(peerThrowArgs("del",p.ServerIP)...);e!=nil{return e}
 }
 if route{
  if _,e=s.run(routeDel(p.Tun)...);e!=nil{return e}
 }
 if e=s.requireEmpty(p);e!=nil{return e}
 if e=os.Remove(s.journal);e!=nil{return e}
 return parentSync(s.journal)
}
func readAllAppJournal(path string)(AllAppPlan,bool,error){
 f,e:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(e,syscall.ENOENT){return AllAppPlan{},false,nil}
 if e!=nil{return AllAppPlan{},false,e}
 defer f.Close()
 st,e:=f.Stat();if e!=nil{return AllAppPlan{},false,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||
    owner.Uid!=uint32(os.Geteuid())||st.Size()<2||
    st.Size()>maxJournalBytes{return AllAppPlan{},false,fmt.Errorf("foreign all-app journal")}
 raw,e:=io.ReadAll(io.LimitReader(f,maxJournalBytes+1))
 if e!=nil{return AllAppPlan{},false,e}
 dec:=json.NewDecoder(strings.NewReader(string(raw)))
 dec.DisallowUnknownFields()
 var p AllAppPlan
 if e=dec.Decode(&p);e!=nil||!p.valid(){return AllAppPlan{},false,fmt.Errorf("invalid all-app durable journal")}
 if dec.Decode(&struct{}{})!=io.EOF{return AllAppPlan{},false,fmt.Errorf("all-app journal trailing record")}
 return p,true,nil
}
func writeAllAppJournal(path string,p AllAppPlan)error{
 raw,e:=json.Marshal(p);if e!=nil{return e}
 raw=append(raw,'\n')
 if len(raw)>maxJournalBytes{return fmt.Errorf("all-app journal too large")}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
 if e!=nil{return e}
 n,e:=f.Write(raw)
 if e==nil&&n!=len(raw){e=io.ErrShortWrite}
 if e==nil{e=f.Sync()}
 closeErr:=f.Close()
 if e!=nil{return e}
 if closeErr!=nil{return closeErr}
 return parentSync(path)
}
func sameAllAppOwner(a,b AllAppPlan)bool{
 if a.Tun!=b.Tun||a.Underlay!=b.Underlay||
    a.NetworkHandle!=b.NetworkHandle||a.IfIndex!=b.IfIndex||
    len(a.ExcludedAppIDs)!=len(b.ExcludedAppIDs){return false}
 for i,id:=range a.ExcludedAppIDs{
  if id!=b.ExcludedAppIDs[i]{return false}
 }
 return true
}
// NewAllApps is intentionally incompatible with prior single/group owner
// journals. Fail closed rather than hijack/reinterpret old UID rules.
func NewAllApps(run Runner,path string,original AllAppPlan)(session *AllAppSession,retErr error){
 if run==nil{return nil,fmt.Errorf("missing root kernel runner")}
 if e:=ownedDirectory(path);e!=nil{return nil,e}
 lock,e:=openOwnerLock(path);if e!=nil{return nil,e}
 defer func(){if retErr!=nil{_ =lock.Close()}}()
 original.Version=allAppsVersion
 var nonce [16]byte
 if _,e=rand.Read(nonce[:]);e!=nil{return nil,e}
 original.Nonce=hex.EncodeToString(nonce[:])
 if !original.valid(){return nil,fmt.Errorf("invalid bounded all-app UID/Network scope")}
 s:=&AllAppSession{run:run,journal:path,plan:original,lock:lock}
 version,exists,e:=readOwnedJournalVersion(path)
 if e!=nil{return nil,e}
 if exists{
  if version!=allAppsVersion&&version!=legacyAllAppsVersion{
   return nil,fmt.Errorf("prior UID owner journal requires exact legacy Stop")
  }
  old,ok,readErr:=readAllAppJournal(path)
  if readErr!=nil||!ok{return nil,fmt.Errorf("invalid previous all-app journal: %w",readErr)}
  if !sameAllAppOwner(old,original){
   return nil,fmt.Errorf("foreign prior all-app generation: manual recovery required")
  }
  if e=s.removeExact(old);e!=nil{return nil,e}
 }
 if e=s.requireEmpty(original);e!=nil{return nil,e}
 if e=writeAllAppJournal(path,original);e!=nil{return nil,e}
 if _,e=s.run(routeAdd(original.Tun)...);e!=nil{
  return nil,errors.Join(e,s.removeExact(original))
 }
 route,peer,direct,rules,e:=s.query(original)
 if e!=nil||!route||peer||anyDirectPresent(direct)||anyRules(rules){
  return nil,errors.Join(fmt.Errorf("all-app route-only readback mismatch: %w",e),s.removeExact(original))
 }
 // Durable journal + default TUN precede an exact /32 exception, which
 // MUST pass readback BEFORE installing the first App UID route.
 if _,e=s.run(peerThrowArgs("add",original.ServerIP)...);e!=nil{
  return nil,errors.Join(e,s.removeExact(original))
 }
 route,peer,direct,rules,e=s.query(original)
 if e!=nil||!route||!peer||anyDirectPresent(direct)||anyRules(rules){
  return nil,errors.Join(fmt.Errorf("all-app peer exception readback mismatch: %w",e),s.removeExact(original))
 }
 // Apply explicit direct prefixes in the SAME private UID FIB,
 // before any App UID rule can route new business.
 for index,cidr:=range original.DirectCIDRs{
  if _,e=s.run(directArgs("add",cidr)...);e!=nil{
   return nil,errors.Join(e,s.removeExact(original))
  }
  _,_,seen,_,checkErr:=s.query(original)
  if checkErr!=nil||len(seen)<=index||!seen[index]{
   return nil,errors.Join(fmt.Errorf("direct prefix %d missing FIB readback: %w",index,checkErr),
    s.removeExact(original))
  }
 }
 for i,r:=range original.ranges(){
  if _,e=s.run(allRuleArgs("add",r,i)...);e!=nil{
   return nil,errors.Join(e,s.removeExact(original))
  }
  _,peerReadback,directReadback,readback,checkErr:=s.query(original)
  if checkErr!=nil||!peerReadback||!allDirectPresent(directReadback)||!readback[i]{
   return nil,errors.Join(fmt.Errorf("all-app uidrange #%d missing kernel readback: %w",i,checkErr),
      s.removeExact(original))
  }
 }
 if e=s.requireReady(original);e!=nil{
  return nil,errors.Join(e,s.removeExact(original))
 }
 s.active=true
 return s,nil
}
func (s *AllAppSession) Stop()error{
 if s==nil||!s.active{return nil}
 if e:=s.removeExact(s.plan);e!=nil{return e}
 s.active=false
 if s.lock!=nil{
  e:=s.lock.Close();s.lock=nil;return e
 }
 return nil
}
