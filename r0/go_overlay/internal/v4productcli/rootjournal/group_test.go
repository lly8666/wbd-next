package rootjournal

import (
 "encoding/json"
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

type groupFake struct {
 tun string
 route bool
 peerThrow string
 rules map[int]int // priority -> exact UID
 foreign string
 failAddAt int
 failDelete bool
 adds int
 calls []string
}
func (f *groupFake) run(args ...string)(string,error){
 key:=strings.Join(args," ")
 f.calls=append(f.calls,key)
 switch{
 case reflect.DeepEqual(args,routeShow()):
  if f.foreign=="route"{return "default dev foreign0\n",nil}
  out:=""
  if f.route{out+="default dev "+f.tun+" scope link\n"}
  if f.peerThrow!=""{out+="throw "+f.peerThrow+"\n"}
  return out,nil
 case reflect.DeepEqual(args,ruleShow()):
  var p []int
  for priority:=range f.rules{p=append(p,priority)}
  sort.Ints(p)
  lines:=[]string{"0: from all lookup local","32766: from all lookup main"}
  for _,priority:=range p{
   uid:=f.rules[priority]
   lines=append(lines,fmt.Sprintf("%d: from all uidrange %d-%d lookup %d",
    priority,uid,uid,Table))
  }
  if f.foreign=="table"{
   lines=append(lines,fmt.Sprintf("%d: from all uidrange 30000-30000 lookup %d",
    Priority+100,Table))
  }
  if f.foreign=="pref"{
   lines=append(lines,fmt.Sprintf("%d: from all uidrange 30000-30000 lookup 99999",
    Priority+GroupMaxUIDs-1))
  }
  return strings.Join(lines,"\n")+"\n",nil
 case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[2]=="add"&&args[3]=="throw":
  if !f.route||f.peerThrow!=""{return "",errors.New("peer throw occupied")}
  f.peerThrow=strings.TrimSuffix(args[4],"/32");return "",nil
 case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[2]=="del"&&args[3]=="throw":
  if f.failDelete||f.peerThrow!=strings.TrimSuffix(args[4],"/32"){return "",errors.New("peer exception foreign")}
  f.peerThrow="";return "",nil
 case len(args)>3&&args[0]=="-4"&&args[1]=="route"&&args[2]=="add":
  if f.route{return "",errors.New("route exists")}
  f.route=true;return "",nil
 case len(args)>3&&args[0]=="-4"&&args[1]=="route"&&args[2]=="del":
  if f.failDelete{return "",errors.New("route deletion refused")}
  if !f.route||f.peerThrow!=""{return "",errors.New("route missing or peer active")}
  f.route=false;return "",nil
 case len(args)>3&&args[0]=="-4"&&args[1]=="rule"&&args[2]=="add":
  f.adds++
  if f.failAddAt==f.adds{return "",errors.New("injected second rule add failure")}
  pref,e:=strconv.Atoi(args[4]);if e!=nil{return "",e}
  u,_:=strconv.Atoi(strings.Split(args[6],"-")[0])
  if _,exists:=f.rules[pref];exists{return "",errors.New("rule exists")}
  f.rules[pref]=u;return "",nil
 case len(args)>3&&args[0]=="-4"&&args[1]=="rule"&&args[2]=="del":
  if f.failDelete{return "",errors.New("rule deletion refused")}
  pref,e:=strconv.Atoi(args[4]);if e!=nil{return "",e}
  u,_:=strconv.Atoi(strings.Split(args[6],"-")[0])
  if f.rules[pref]!=u{return "",errors.New("wrong owned UID rule")}
  delete(f.rules,pref);return "",nil
 default:
  return "",fmt.Errorf("unexpected ip command: %s",key)
 }
}
func groupFixture(t *testing.T)(*groupFake,string,GroupPlan){
 t.Helper()
 path:=filepath.Join(t.TempDir(),"only-root","route-journal.json")
 p:=GroupPlan{UIDs:[]int{10011,10035,10091},Tun:"wbdv40",
  Lease:"10.66.0.8/32",Underlay:"wlan0",IfIndex:23,NetworkHandle:153}
 return &groupFake{tun:p.Tun,rules:make(map[int]int)},path,p
}
func TestGroupExactThreeUIDsDurableCommitAndStop(t *testing.T){
 f,path,p:=groupFixture(t)
 s,err:=NewGroup(f.run,path,p);if err!=nil{t.Fatal(err)}
 if !f.route||len(f.rules)!=3{t.Fatal("route group not fully installed")}
 for i,uid:=range p.UIDs {
  if f.rules[Priority+i]!=uid{t.Fatalf("unexpected rule priority %d",Priority+i)}
 }
 raw,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 var receipt GroupPlan
 if err=json.Unmarshal(raw,&receipt);err!=nil{t.Fatal(err)}
 if receipt.Version!=groupVersion||!reflect.DeepEqual(receipt.UIDs,p.UIDs){
  t.Fatalf("not durable group receipt: %#v",receipt)
 }
 if err=s.Stop();err!=nil{t.Fatal(err)}
 if f.route||len(f.rules)!=0{t.Fatal("orphaned private kernel state")}
 if err=s.Stop();err!=nil{t.Fatal("non-idempotent Stop")}
 if _,err=os.Stat(path);!os.IsNotExist(err){t.Fatal("journal not deleted",err)}
 for _,command:=range f.calls {
  if strings.Contains(command,"rule flush")||
   strings.Contains(command,"iptables")||
   strings.Contains(command,"sysctl")||
   strings.Contains(command,"route add default dev wlan0 table main") {
   t.Fatalf("global mutation: %s",command)
  }
 }
}
func TestGroupPartialRuleFailureRollback(t *testing.T){
 f,path,p:=groupFixture(t)
 f.failAddAt=2
 if _,err:=NewGroup(f.run,path,p);err==nil{t.Fatal("accepted partial group")}
 if f.route||len(f.rules)>0{t.Fatal("partial rules leaked")}
 if _,err:=os.Stat(path);!os.IsNotExist(err){t.Fatal("journal retained despite proven rollback",err)}
}
func TestGroupCrashRecoveryAndLiveOwnerExclusion(t *testing.T){
 for _,stage:=range []string{"journal","route","first","ready"}{
  t.Run(stage,func(t *testing.T){
   f,path,p:=groupFixture(t)
   s,err:=NewGroup(f.run,path,p);if err!=nil{t.Fatal(err)}
   if _,err=NewGroup(f.run,path,p);err==nil{
    t.Fatal("second owner stole live flock")
   }
   switch stage {
   case "journal":f.route=false;f.rules=make(map[int]int)
   case "route":f.rules=make(map[int]int)
   case "first":delete(f.rules,Priority+1);delete(f.rules,Priority+2)
   }
   // Simulate actual process death: kernel releases flock, and never
   // calls the old Stop. New owner must recover exact persistent state.
   if err=s.lock.Close();err!=nil{t.Fatal(err)}
   s.lock=nil;s.active=false
   resumed,err:=NewGroup(f.run,path,p)
   if err!=nil{t.Fatal("group crash recovery refused",err)}
   if !f.route||len(f.rules)!=3{t.Fatal("not fully re-established")}
   if err=resumed.Stop();err!=nil{t.Fatal(err)}
  })
 }
}
func TestGroupForeignStateRejectWithoutKernelMutation(t *testing.T){
 for _,foreign:=range []string{"route","table","pref"}{
  t.Run(foreign,func(t *testing.T){
   f,path,p:=groupFixture(t);f.foreign=foreign
   if _,err:=NewGroup(f.run,path,p);err==nil{t.Fatal("accepted foreign rule/table")}
   if f.route||len(f.rules)!=0{t.Fatal("touched foreign kernel state")}
  })
 }
}
func TestGroupRejectUntrustedUIDsAndLease(t *testing.T){
 for _,uids:=range [][]int{{},{10010},{10011,10011},{10035,10011},
  {0,10011},{9999,10011},{10011,2000000},
  {10001,10002,10003,10004,10005,10006,10007,10008,
   10009,10010,10011,10012,10013,10014,10015,10016,10017}}{
  f,path,p:=groupFixture(t);p.UIDs=uids
  if _,err:=NewGroup(f.run,path,p);err==nil{t.Fatalf("accepted invalid UIDs %v",uids)}
 }
 f,path,p:=groupFixture(t);p.Lease="10.66.0.0/24"
 if _,err:=NewGroup(f.run,path,p);err==nil{t.Fatal("accepted untrusted broad lease")}
}
func TestGroupForeignPreviousUIDSetRefused(t *testing.T){
 f,path,p:=groupFixture(t)
 s,err:=NewGroup(f.run,path,p);if err!=nil{t.Fatal(err)}
 _=s.lock.Close();s.lock=nil;s.active=false
 p.UIDs=[]int{10011,10035,10100}
 if _,err=NewGroup(f.run,path,p);err==nil{t.Fatal("cross-owned previous group recovered")}
 if !f.route||len(f.rules)!=3{t.Fatal("mutated unrelated prior group")}
}
func TestLegacySingleUpgradeAndGroupDowngradeAfterCrash(t *testing.T){
 f,path,p:=groupFixture(t)
 legacy:=Plan{UID:p.UIDs[0],Tun:p.Tun,Lease:p.Lease,
  Underlay:p.Underlay,IfIndex:p.IfIndex,NetworkHandle:p.NetworkHandle}
 one,err:=New(f.run,path,legacy);if err!=nil{t.Fatal("legacy root install",err)}
 _=one.lock.Close();one.lock=nil;one.active=false
 group,err:=NewGroup(f.run,path,p)
 if err!=nil{t.Fatal("single->group recovery",err)}
 if !f.route||len(f.rules)!=len(p.UIDs){t.Fatal("group not installed")}
 _=group.lock.Close();group.lock=nil;group.active=false
 single,err:=New(f.run,path,legacy)
 if err!=nil{t.Fatal("group->single recovery",err)}
 if !f.route||len(f.rules)!=1||f.rules[Priority]!=p.UIDs[0]{
  t.Fatal("single not restored correctly")
 }
 if err=single.Stop();err!=nil{t.Fatal(err)}
}
func TestGroupStopFailureKeepsJournalAndAllowsExactRecovery(t *testing.T){
 f,path,p:=groupFixture(t)
 s,err:=NewGroup(f.run,path,p);if err!=nil{t.Fatal(err)}
 f.failDelete=true
 if err=s.Stop();err==nil{t.Fatal("pretended successful Stop")}
 if _,err=os.Stat(path);err!=nil{t.Fatal("durable journal missing despite kernel mutation failure",err)}
 f.failDelete=false
 if err=s.Stop();err!=nil{t.Fatal("cannot retry exact Stop",err)}
}

// B31: selected group uses same private FIB peer throw as all-app.
func TestB31GroupServerPeerThrowBeforeRulesAndStop(t *testing.T){
 f,path,plan:=groupFixture(t);plan.ServerIP="203.0.113.9"
 s,err:=NewGroup(f.run,path,plan);if err!=nil{t.Fatal(err)}
 if !f.route||f.peerThrow!=plan.ServerIP||len(f.rules)!=len(plan.UIDs){
  t.Fatal("missing grouped App peer route")
 }
 throwAt,firstRule:=-1,-1
 for i,line:=range f.calls{
  if strings.Contains(line,"route add throw 203.0.113.9/32"){throwAt=i}
  if strings.Contains(line,"rule add pref")&&firstRule<0{firstRule=i}
 }
 if throwAt<0||firstRule<0||throwAt>=firstRule{t.Fatal("group peer route late")}
 if err=s.Stop();err!=nil{t.Fatal(err)}
 if f.route||f.peerThrow!=""||len(f.rules)!=0{t.Fatal("group Stop leaked route")}
}
func TestB31GroupForeignPeerRouteNotRemoved(t *testing.T){
 f,path,plan:=groupFixture(t);plan.ServerIP="203.0.113.9"
 s,err:=NewGroup(f.run,path,plan);if err!=nil{t.Fatal(err)}
 f.peerThrow="198.51.100.11"
 if err=s.Stop();err==nil{t.Fatal("foreign route should block owned Stop")}
 if _,err:=os.Stat(path);err!=nil{t.Fatal("journal missing on foreign route",err)}
 f.peerThrow=plan.ServerIP
 if err=s.Stop();err!=nil{t.Fatal(err)}
}

func TestB58SixteenRealSelectedUIDsBoundedKernelReadbacks(t *testing.T){
 f,path,plan:=groupFixture(t)
 plan.UIDs=make([]int,16)
 for i:=range plan.UIDs{plan.UIDs[i]=11100+i}
 owner,err:=NewGroup(f.run,path,plan)
 if err!=nil{t.Fatal(err)}
 adds,reads:=0,0
 for _,call:=range f.calls{
  if strings.Contains(call," rule add pref "){adds++}
  if strings.Contains(call," route show table ")||
   strings.Contains(call," rule show"){reads++}
 }
 if adds!=16||len(f.rules)!=16{t.Fatalf("missing 16 UID rules: %d %d",adds,len(f.rules))}
 if reads>12{t.Fatalf("group installation still rechecks whole FIB per UID: %d",reads)}
 if err=owner.Stop();err!=nil{t.Fatal(err)}
 if len(f.rules)!=0||f.route{t.Fatal("16-UID route Stop did not withdraw")}
}
