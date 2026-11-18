package rootjournal

import (
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "reflect"
 "sort"
 "strconv"
 "strings"
 "testing"
)
type allFakeIP struct{
 tun string
 route bool
 peerThrow string
 failPeerAdd bool
 rules map[int]allRange
 failAddAt int
 addCount int
 failDelete bool
 foreign bool
 calls []string
}
func(f *allFakeIP)run(args ...string)(string,error){
 text:=strings.Join(args," ")
 f.calls=append(f.calls,text)
 switch{
 case reflect.DeepEqual(args,routeShow()):
  out:=""
  if f.route{out+="default dev "+f.tun+" scope link\n"}
  if f.peerThrow!=""{out+="throw "+f.peerThrow+"\n"}
  return out,nil
 case reflect.DeepEqual(args,ruleShow()):
  lines:=[]string{"0: from all lookup local","32766: from all lookup main"}
  prefs:=make([]int,0,len(f.rules))
  for k:=range f.rules{prefs=append(prefs,k)}
  sort.Ints(prefs)
  for _,pref:=range prefs{
   r:=f.rules[pref]
   lines=append(lines,fmt.Sprintf("%d: from all uidrange %d-%d lookup %d",pref,r.from,r.to,Table))
  }
  if f.foreign{
   lines=append(lines,fmt.Sprintf("%d: from all uidrange 10001-10002 lookup 99999",Priority))
  }
  return strings.Join(lines,"\n")+"\n",nil
 case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[2]=="add"&&args[3]=="throw":
  if f.failPeerAdd{return "",errors.New("injected peer exception failure")}
  if f.peerThrow!=""||!f.route{return "",errors.New("throw occupied")}
  f.peerThrow=strings.TrimSuffix(args[4],"/32");return "",nil
 case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[2]=="del"&&args[3]=="throw":
  if f.failDelete{return "",errors.New("delete denied")}
  if f.peerThrow!=strings.TrimSuffix(args[4],"/32"){return "",errors.New("foreign throw")}
  f.peerThrow="";return "",nil
 case reflect.DeepEqual(args,routeAdd(f.tun)):
  if f.route{return "",errors.New("default occupied")}
  f.route=true;return "",nil
 case reflect.DeepEqual(args,routeDel(f.tun)):
  if f.failDelete{return "",errors.New("delete denied")}
  if !f.route||f.peerThrow!=""{return "",errors.New("active peer exception")}
  f.route=false;return "",nil
 case len(args)>6&&args[0]=="-4"&&args[1]=="rule"&&args[2]=="add":
  f.addCount++
  if f.failAddAt==f.addCount{return "",errors.New("injected kernel rule failure")}
  pref,e:=strconv.Atoi(args[4]);if e!=nil{return "",e}
  parts:=strings.Split(args[6],"-")
  from,e:=strconv.Atoi(parts[0]);if e!=nil{return "",e}
  to,e:=strconv.Atoi(parts[1]);if e!=nil{return "",e}
  if _,exists:=f.rules[pref];exists{return "",errors.New("occupied priority")}
  f.rules[pref]=allRange{from,to};return "",nil
 case len(args)>6&&args[0]=="-4"&&args[1]=="rule"&&args[2]=="del":
  if f.failDelete{return "",errors.New("delete denied")}
  pref,e:=strconv.Atoi(args[4]);if e!=nil{return "",e}
  parts:=strings.Split(args[6],"-")
  from,_:=strconv.Atoi(parts[0]);to,_:=strconv.Atoi(parts[1])
  if r,ok:=f.rules[pref];!ok||r!=(allRange{from,to}){return "",errors.New("foreign rule")}
  delete(f.rules,pref);return "",nil
 }
 return "",fmt.Errorf("unexpected ip command: %s",text)
}
func allFixture(t *testing.T)(*allFakeIP,string,AllAppPlan){
 t.Helper()
 path:=filepath.Join(t.TempDir(),"root","route-journal.json")
 p:=AllAppPlan{ExcludedAppIDs:[]int{10111,10222},Tun:"wbdv40",
  Underlay:"wlan0",Lease:"10.66.0.8/32",ServerIP:"203.0.113.9",
  NetworkHandle:154,IfIndex:13}
 return &allFakeIP{tun:p.Tun,rules:make(map[int]allRange)},path,p
}
func containsAllAppUID(rs []allRange,uid int)bool{
 for _,r:=range rs{if uid>=r.from&&uid<=r.to{return true}}
 return false
}
func TestAllAppRangeDoesNotCaptureRootOrSystemAcrossProfiles(t *testing.T){
 _,_,p:=allFixture(t)
 rs:=p.ranges()
 if len(rs)!=60{t.Fatalf("expected 60 disjoint ranges for 20 profiles: %d",len(rs))}
 for _,uid:=range []int{0,1000,9999,10111,10222,100000,101000,110111,110222,1999999}{
  if containsAllAppUID(rs,uid){t.Fatalf("captured root/system/controller/manager UID %d",uid)}
 }
 for _,uid:=range []int{10000,10001,10555,19999,110000,119999,1910000,1919999}{
  if !containsAllAppUID(rs,uid){t.Fatalf("did not route ordinary app UID %d",uid)}
 }
 for i:=1;i<len(rs);i++{if rs[i].from<=rs[i-1].to{t.Fatal("overlapping full-device UID ranges")}}
}
func TestAllAppDurableKernelReadbackAndExactStop(t *testing.T){
 f,path,p:=allFixture(t)
 s,err:=NewAllApps(f.run,path,p);if err!=nil{t.Fatal(err)}
 if !f.route||f.peerThrow!=p.ServerIP||len(f.rules)!=len(p.ranges()){
  t.Fatal("server bypass / app UID range incomplete")
 }
 raw,e:=os.ReadFile(path);if e!=nil{t.Fatal(e)}
 if !strings.Contains(string(raw),"\"version\":4")||
  !strings.Contains(string(raw),"\"server_ip\":\"203.0.113.9\"")||
  !strings.Contains(string(raw),"\"excluded_app_ids\""){
  t.Fatal("missing durable exclusions or version")
 }
 if err=s.Stop();err!=nil{t.Fatal(err)}
 if f.route||f.peerThrow!=""||len(f.rules)!=0{t.Fatal("route/throw/UID leak after Stop")}
 if err=s.Stop();err!=nil{t.Fatal("Stop not idempotent")}
 if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatal("journal not removed after readback")}
 for _,command:=range f.calls{
  if strings.Contains(command,"flush")||strings.Contains(command,"iptables")||
     strings.Contains(command,"sysctl")||strings.Contains(command,"main"){
   t.Fatal("unsafe global mutation",command)
  }
 }
}
func TestAllAppFailureAtomicRollback(t *testing.T){
 f,path,p:=allFixture(t)
 f.failAddAt=3
 if _,err:=NewAllApps(f.run,path,p);err==nil{t.Fatal("claimed readiness after failure")}
 if f.route||f.peerThrow!=""||len(f.rules)!=0{t.Fatal("partial kernel route/throw/rules leaked")}
 if _,err:=os.Stat(path);!os.IsNotExist(err){t.Fatal("journal retained after successful rollback")}
}
func TestAllAppCrashRecoveryOwnerExclusionAndForeignScope(t *testing.T){
 f,path,p:=allFixture(t)
 s,err:=NewAllApps(f.run,path,p);if err!=nil{t.Fatal(err)}
 if _,e:=NewAllApps(f.run,path,p);e==nil{t.Fatal("stole live kernel owner")}
 if e:=s.lock.Close();e!=nil{t.Fatal(e)}
 s.lock=nil;s.active=false
 delete(f.rules,Priority+len(p.ranges())-1)
 resumed,err:=NewAllApps(f.run,path,p);if err!=nil{t.Fatal("crash recovery",err)}
 if !f.route||f.peerThrow!=p.ServerIP||len(f.rules)!=len(p.ranges()){
  t.Fatal("incomplete recovered server bypass/UID policy")
 }
 if err=resumed.Stop();err!=nil{t.Fatal(err)}
}
func TestAllAppRejectChangedExclusionsAndForeignPriority(t *testing.T){
 f,path,p:=allFixture(t)
 s,err:=NewAllApps(f.run,path,p);if err!=nil{t.Fatal(err)}
 _=s.lock.Close();s.lock=nil;s.active=false
 p.ExcludedAppIDs=[]int{10111,10333}
 if _,err:=NewAllApps(f.run,path,p);err==nil{t.Fatal("stole another manager UID exclusions")}
 if !f.route{t.Fatal("changed foreign prior route")}
 g,q,v:=allFixture(t);g.foreign=true
 if _,err:=NewAllApps(g.run,q,v);err==nil{t.Fatal("mutated foreign UID priority")}
 if g.route||len(g.rules)!=0{t.Fatal("foreign rule mutated")}
}
func TestAllAppInvalidExclusionsAndLeaseFailClosed(t *testing.T){
 invalid:=[][]int{{},{10111},{10111,10111},{10222,10111},
   {9999,10222},{10111,20000},{10111,10222,10333,10444,10555,10666,10777,10888,10999}}
 for _,uids:=range invalid{
  f,path,p:=allFixture(t);p.ExcludedAppIDs=uids
  if _,err:=NewAllApps(f.run,path,p);err==nil{t.Fatalf("accepted %v",uids)}
 }
 f,path,p:=allFixture(t);p.Lease="10.66.0.0/24"
 if _,err:=NewAllApps(f.run,path,p);err==nil{t.Fatal("accepted unauthenticated /24")}
}

func TestAllAppsServerIPExclusionBeforeUIDsAndRollback(t *testing.T){
 f,path,p:=allFixture(t);f.failPeerAdd=true
 if _,err:=NewAllApps(f.run,path,p);err==nil{t.Fatal("must reject unavailable peer bypass")}
 if f.route||f.peerThrow!=""||len(f.rules)!=0{t.Fatal("failed bypass leaked a rule/route")}
 for _,call:=range f.calls{if strings.Contains(call," rule add "){t.Fatal("UID routed before peer exception")}}
 for _,invalid:=range []string{"","0.0.0.0","127.0.0.1","169.254.1.2","224.0.0.1","203.0.113.09","10.66.0.8"}{
  n,q,v:=allFixture(t);v.ServerIP=invalid
  if _,err:=NewAllApps(n.run,q,v);err==nil{t.Fatalf("invalid server exclusion admitted: %q",invalid)}
 }
}
func TestAllAppsServerThrowRejectsForeignRoute(t *testing.T){
 good:="default dev wbdv40 scope link\nthrow 203.0.113.9\n"
 a,b,e:=allAppRouteState(good,"wbdv40","203.0.113.9")
 if e!=nil||!a||!b{t.Fatalf("exact exception rejected: %v",e)}
 for _,bad:=range []string{
  "default dev wbdv40\nthrow 203.0.113.10\n",
  "default dev wbdv40\nthrow 203.0.113.9 metric 1\n",
  "default dev wbdv40\nthrow 203.0.113.9\nthrow 203.0.113.9\n",
  "default dev wlan0\nthrow 203.0.113.9\n",
 }{
  a,b,e:=allAppRouteState(bad,"wbdv40","203.0.113.9")
  if e==nil&&a&&b{t.Fatalf("foreign exception accepted: %q",bad)}
 }
}

func TestAllAppsPreviousV3OwnedJournalExactRecoveryToV4(t *testing.T){
 f,path,p:=allFixture(t)
 old:=p
 old.Version=legacyAllAppsVersion
 old.ServerIP=""
 old.Nonce="0123456789abcdef0123456789abcdef"
 if e:=ownedDirectory(path);e!=nil{t.Fatal(e)}
 if e:=writeAllAppJournal(path,old);e!=nil{t.Fatal(e)}
 f.route=true
 s,e:=NewAllApps(f.run,path,p)
 if e!=nil{t.Fatalf("v3 exact recovery to v4 failed: %v",e)}
 if f.peerThrow!=p.ServerIP||!f.route||len(f.rules)!=len(p.ranges()){
  t.Fatal("v3 migration did not install v4 peer exception")
 }
 if e=s.Stop();e!=nil{t.Fatal(e)}
 if f.route||f.peerThrow!=""||len(f.rules)!=0{
  t.Fatal("v3->v4 cleanup left any owner state")
 }
}
