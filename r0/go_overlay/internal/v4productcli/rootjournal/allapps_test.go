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
  if f.route{return "default dev "+f.tun+" scope link\n",nil}
  return "",nil
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
 case len(args)>2&&args[0]=="-4"&&args[1]=="route"&&args[2]=="add":
  if f.route{return "",errors.New("route occupied")}
  f.route=true;return "",nil
 case len(args)>2&&args[0]=="-4"&&args[1]=="route"&&args[2]=="del":
  if f.failDelete{return "",errors.New("delete denied")}
  if !f.route{return "",errors.New("missing route")}
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
  Underlay:"wlan0",Lease:"10.66.0.8/32",NetworkHandle:154,IfIndex:13}
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
 if !f.route||len(f.rules)!=len(p.ranges()){t.Fatal("kernel UID range incomplete")}
 raw,e:=os.ReadFile(path);if e!=nil{t.Fatal(e)}
 if !strings.Contains(string(raw),"\"version\":3")||!strings.Contains(string(raw),"\"excluded_app_ids\""){
  t.Fatal("missing durable exclusions or version")
 }
 if err=s.Stop();err!=nil{t.Fatal(err)}
 if f.route||len(f.rules)!=0{t.Fatal("kernel route/rules leaked on Stop")}
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
 if f.route||len(f.rules)!=0{t.Fatal("partial kernel rules leaked")}
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
 if !f.route||len(f.rules)!=len(p.ranges()){t.Fatal("incomplete restored kernel state")}
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
