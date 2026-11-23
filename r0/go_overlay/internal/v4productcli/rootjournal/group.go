package rootjournal

// Group routing keeps ONE authenticated TUN lease and dedicated FIB table,
// but grants up to sixteen canonical ordinary Android application UIDs.
// All kernel mutations are cold-only, journal-first and exactly reversible.
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

const GroupMaxUIDs = 16
const groupVersion = 2

type GroupPlan struct {
 Version int `json:"version"`
 UIDs []int `json:"uids"`
 Tun string `json:"tun"`
 Lease string `json:"lease"`
 ServerIP string `json:"server_ip,omitempty"`
 DirectCIDRs []string `json:"direct_cidrs,omitempty"`
 Underlay string `json:"underlay"`
 NetworkHandle uint64 `json:"network_handle"`
 IfIndex int `json:"ifindex"`
 Nonce string `json:"nonce"`
}

type GroupSession struct {
 run Runner
 journal string
 plan GroupPlan
 active bool
 lock *os.File
}

func ValidGroupUIDs(uids []int) bool {
 if len(uids)<2||len(uids)>GroupMaxUIDs{return false}
 previous:=0
 for _,uid:=range uids {
  if uid<10000||uid>1999999||uid<=previous{return false}
  previous=uid
 }
 return true
}
func (p GroupPlan) valid() bool {
 lease,err:=netip.ParsePrefix(p.Lease)
 return p.Version==groupVersion&&ValidGroupUIDs(p.UIDs)&&
  err==nil&&lease.IsValid()&&lease.Addr().Is4()&&lease.Bits()==32&&
  !lease.Addr().IsUnspecified()&&!lease.Addr().IsMulticast()&&
  (p.ServerIP==""||(validServerPeerIPv4(p.ServerIP)&&
   p.ServerIP!=lease.Addr().String()))&&
  validDirectCIDRs(p.DirectCIDRs,p.ServerIP)&&
  nameOK(p.Tun)&&nameOK(p.Underlay)&&p.Tun!=p.Underlay&&
  p.NetworkHandle!=0&&p.IfIndex>0&&len(p.Nonce)==32
}
func sameGroupOwner(a,b GroupPlan) bool {
 if a.Tun!=b.Tun||a.Underlay!=b.Underlay||
  len(a.UIDs)!=len(b.UIDs){return false}
 for i,uid:=range a.UIDs {if uid!=b.UIDs[i]{return false}}
 return true
}
func hasUID(uids []int,uid int)bool{
 for _,one:=range uids{if one==uid{return true}}
 return false
}
func groupRuleArgs(action string,uid,offset int) []string {
 return []string{"-4","rule",action,"pref",strconv.Itoa(Priority+offset),
  "uidrange",fmt.Sprintf("%d-%d",uid,uid),"lookup",strconv.Itoa(Table)}
}
// Consume the real 'ip -4 rule show' text and refuse ANY foreign use of
// reserved priorities or the owned table, even if it uses a different UID.
func groupRuleState(out string,p GroupPlan)([]bool,error){
 present:=make([]bool,len(p.UIDs))
 for _,line:=range strings.Split(out,"\n"){
  words:=strings.Fields(line)
  if len(words)==0{continue}
  pref,err:=strconv.Atoi(strings.TrimSuffix(words[0],":"))
  if err!=nil{return nil,fmt.Errorf("unparseable Android ip rule priority")}
  hasTable,hasUID,uid:=false,false,0
  for i:=1;i+1<len(words);i++{
   if (words[i]=="lookup"||words[i]=="table")&&
       words[i+1]==strconv.Itoa(Table){hasTable=true}
   if words[i]=="uidrange"{
    hasUID=true
    parts:=strings.Split(words[i+1],"-")
    if len(parts)==2&&parts[0]==parts[1]{uid,_=strconv.Atoi(parts[0])}
   }
  }
  reserved:=pref>=Priority&&pref<Priority+GroupMaxUIDs
  if !reserved&&!hasTable{continue}
  offset:=pref-Priority
  if !reserved||offset<0||offset>=len(p.UIDs)||
    !hasTable||!hasUID||uid!=p.UIDs[offset]||present[offset]||
    !strictOwnedUIDRule(words,pref,p.UIDs[offset]){
   return nil,fmt.Errorf("foreign or duplicate Android group rule: priority %d",pref)
  }
  present[offset]=true
 }
 return present,nil
}
func groupRead(path string)(GroupPlan,bool,error){
 f,err:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(err,syscall.ENOENT){return GroupPlan{},false,nil}
 if err!=nil{return GroupPlan{},false,err}
 defer f.Close()
 st,err:=f.Stat()
 if err!=nil{return GroupPlan{},false,err}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||
  owner.Uid!=uint32(os.Geteuid())||st.Size()<2||
  st.Size()>maxJournalBytes{return GroupPlan{},false,fmt.Errorf("foreign group journal")}
 raw,err:=io.ReadAll(io.LimitReader(f,maxJournalBytes+1))
 if err!=nil{return GroupPlan{},false,err}
 dec:=json.NewDecoder(strings.NewReader(string(raw)))
 dec.DisallowUnknownFields()
 var p GroupPlan
 if err=dec.Decode(&p);err!=nil||!p.valid(){
  return GroupPlan{},false,fmt.Errorf("invalid owned group journal")
 }
 if dec.Decode(&struct{}{})!=io.EOF{
  return GroupPlan{},false,fmt.Errorf("group journal has trailing data")
 }
 return p,true,nil
}
func groupWrite(path string,p GroupPlan)error{
 raw,err:=json.Marshal(p)
 if err!=nil{return err}
 raw=append(raw,'\n')
 if len(raw)>maxJournalBytes{return fmt.Errorf("group journal too large")}
 f,err:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
 if err!=nil{return err}
 n,writeErr:=f.Write(raw)
 if writeErr==nil&&n!=len(raw){writeErr=io.ErrShortWrite}
 if writeErr==nil{writeErr=f.Sync()}
 closeErr:=f.Close()
 if writeErr!=nil{return writeErr}
 if closeErr!=nil{return closeErr}
 return parentSync(path)
}
func (s *GroupSession) query(p GroupPlan)(bool,bool,[]bool,[]bool,error){
 out,err:=s.run(routeShow()...)
 if err!=nil{return false,false,nil,nil,err}
 route,peer,direct,err:=routeWithDirect(out,p.Tun,p.ServerIP,p.DirectCIDRs)
 if err!=nil{return false,false,nil,nil,err}
 lines,err:=s.run(ruleShow()...)
 if err!=nil{return false,false,nil,nil,err}
 rules,err:=groupRuleState(lines,p)
 return route,peer,direct,rules,err
}
func anyRules(b []bool)bool{
 for _,v:=range b{if v{return true}}
 return false
}
func allRules(b []bool)bool{
 for _,v:=range b{if !v{return false}}
 return true
}
func (s *GroupSession) requireEmpty(p GroupPlan)error{
 route,peer,direct,rules,err:=s.query(p)
 if err!=nil{return err}
 if route||peer||anyDirectPresent(direct)||anyRules(rules){
  return fmt.Errorf("Android group table/rules occupied")
 }
 return nil
}
func (s *GroupSession) requireRouteOnly(p GroupPlan)error{
 route,peer,direct,rules,err:=s.query(p)
 if err!=nil{return err}
 if !route||peer||anyDirectPresent(direct)||anyRules(rules){
  return fmt.Errorf("Android group route-only mismatch")
 }
 return nil
}
func (s *GroupSession) requirePeerRouteOnly(p GroupPlan)error{
 route,peer,direct,rules,err:=s.query(p)
 if err!=nil{return err}
 if !route||!peer||anyDirectPresent(direct)||anyRules(rules){
  return fmt.Errorf("Android group peer-only mismatch")
 }
 return nil
}
func (s *GroupSession) requireReady(p GroupPlan)error{
 route,peer,direct,rules,err:=s.query(p)
 if err!=nil{return err}
 if !route||(p.ServerIP!=""&&!peer)||
  !allDirectPresent(direct)||!allRules(rules){
  return fmt.Errorf("Android group UID/direct/peer readback mismatch")
 }
 return nil
}
func (s *GroupSession) removeExact(p GroupPlan)error{
 route,peer,direct,rules,err:=s.query(p)
 if err!=nil{return err}
 for i:=len(rules)-1;i>=0;i--{
  if rules[i]{
   if _,err=s.run(groupRuleArgs("del",p.UIDs[i],i)...);err!=nil{return err}
  }
 }
 for i:=len(direct)-1;i>=0;i--{
  if direct[i]{
   if _,err=s.run(directArgs("del",p.DirectCIDRs[i])...);err!=nil{return err}
  }
 }
 if peer{
  if _,err=s.run(peerThrowArgs("del",p.ServerIP)...);err!=nil{return err}
 }
 if route{
  if _,err=s.run(routeDel(p.Tun)...);err!=nil{return err}
 }
 if err=s.requireEmpty(p);err!=nil{return err}
 if err=os.Remove(s.journal);err!=nil{return err}
 return parentSync(s.journal)
}
func readOwnedJournalVersion(path string)(int,bool,error){
 f,err:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(err,syscall.ENOENT){return 0,false,nil}
 if err!=nil{return 0,false,err}
 defer f.Close()
 st,err:=f.Stat()
 if err!=nil{return 0,false,err}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||
  owner.Uid!=uint32(os.Geteuid())||st.Size()<2||st.Size()>maxJournalBytes{
  return 0,false,fmt.Errorf("invalid root route journal ownership")}
 var envelope struct{Version int `json:"version"`}
 raw,err:=io.ReadAll(io.LimitReader(f,maxJournalBytes+1))
 if err!=nil{return 0,false,err}
 if err=json.Unmarshal(raw,&envelope);err!=nil{return 0,false,err}
 if envelope.Version!=version&&envelope.Version!=groupVersion&&
  envelope.Version!=legacyAllAppsVersion&&envelope.Version!=allAppsVersion{
  return 0,false,fmt.Errorf("foreign root journal version")}
 return envelope.Version,true,nil
}
// NewGroup performs all-or-nothing (with durable crash recovery) for a
// canonical group of 2..8 distinct Android application UIDs. It is mutually
// exclusive with single-UID New by the SAME owner.lock and journal path.
func NewGroup(run Runner,path string,original GroupPlan)(session *GroupSession,retErr error){
 if run==nil{return nil,fmt.Errorf("missing kernel runner")}
 if err:=ownedDirectory(path);err!=nil{return nil,err}
 lock,err:=openOwnerLock(path)
 if err!=nil{return nil,err}
 defer func(){if retErr!=nil{_ =lock.Close()}}()
 original.Version=groupVersion
 var nonce [16]byte
 if _,err=rand.Read(nonce[:]);err!=nil{return nil,err}
 original.Nonce=hex.EncodeToString(nonce[:])
 if !original.valid(){return nil,fmt.Errorf("invalid canonical Android UID group")}
 s:=&GroupSession{run:run,journal:path,plan:original,lock:lock}
 kind,exists,err:=readOwnedJournalVersion(path)
 if err!=nil{return nil,err}
 if exists {
  if kind==version {
   old,found,e:=journalRead(path)
   if e!=nil||!found{return nil,fmt.Errorf("invalid previous single UID journal: %w",e)}
   if old.Tun!=original.Tun||old.Underlay!=original.Underlay||
    !hasUID(original.UIDs,old.UID){
    return nil,fmt.Errorf("foreign previous single UID route generation")}
   legacy:=&Session{run:run,journal:path,plan:old,lock:lock}
   if e=legacy.removeExact(old);e!=nil{return nil,e}
  }else{
   old,found,e:=groupRead(path)
   if e!=nil||!found{return nil,fmt.Errorf("invalid previous group journal: %w",e)}
   if !sameGroupOwner(old,original){
    return nil,fmt.Errorf("foreign prior Android UID group: manual recovery required")}
   if e=s.removeExact(old);e!=nil{return nil,e}
  }
 }
 if err=s.requireEmpty(original);err!=nil{return nil,err}
 if err=groupWrite(path,original);err!=nil{return nil,err}
 if _,err=s.run(routeAdd(original.Tun)...);err!=nil{
  return nil,errors.Join(err,s.removeExact(original))
 }
 if err=s.requireRouteOnly(original);err!=nil{
  return nil,errors.Join(err,s.removeExact(original))
 }
 if original.ServerIP!=""{
  if _,err=s.run(peerThrowArgs("add",original.ServerIP)...);err!=nil{
   return nil,errors.Join(err,s.removeExact(original))
  }
  if err=s.requirePeerRouteOnly(original);err!=nil{
   return nil,errors.Join(err,s.removeExact(original))
  }
 }
 // B58: Every direct prefix is in the existing FIB before any UID is added.
 // A single exact snapshot replaces one route/rule show per prefix.
 for _,cidr:=range original.DirectCIDRs{
  if _,err=s.run(directArgs("add",cidr)...);err!=nil{
   return nil,errors.Join(err,s.removeExact(original))
  }
 }
 if len(original.DirectCIDRs)>0{
  route,peer,direct,rules,checkErr:=s.query(original)
  if checkErr!=nil||!route||(original.ServerIP!=""&&!peer)||
   !allDirectPresent(direct)||anyRules(rules){
   return nil,errors.Join(fmt.Errorf("group direct FIB not ready before UID: %w",checkErr),
    s.removeExact(original))
  }
 }
 // 16 App UIDs use the same one Go /32, one TUN and private table.
 for i,uid:=range original.UIDs {
  if _,err=s.run(groupRuleArgs("add",uid,i)...);err!=nil{
   return nil,errors.Join(err,s.removeExact(original))
  }
 }
 // Exactly one final complete readback before the original READY receipt.
 if err=s.requireReady(original);err!=nil{
  return nil,errors.Join(err,s.removeExact(original))
 }
 s.active=true
 return s,nil
}
func (s *GroupSession) Stop()error{
 if s==nil||!s.active{return nil}
 if err:=s.removeExact(s.plan);err!=nil{return err}
 s.active=false
 if s.lock!=nil{
  err:=s.lock.Close()
  s.lock=nil
  return err
 }
 return nil
}
