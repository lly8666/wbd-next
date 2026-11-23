package rootjournal

import (
 "errors"
 "fmt"
 "os"
 "reflect"
 "sort"
 "strconv"
 "strings"
 "testing"
)

// Single shared fake ip(8) kernel for all three ORIGINAL rooted UID owners.
// It returns actual ip -4 route/rule text and executes the same commands
// production Android Go sends; no replacement dataplane or mock TLS.
type b33RouteKernel struct{
 tun string
 defaultTun bool
 throws map[string]bool
 rules map[int]string
 failCIDR string
 calls []string
}
func (f *b33RouteKernel) run(args ...string)(string,error){
 key:=strings.Join(args," ")
 f.calls=append(f.calls,key)
 switch{
 case reflect.DeepEqual(args,routeShow()):
  lines:=[]string{}
  if f.defaultTun{lines=append(lines,"default dev "+f.tun+" scope link")}
  routes:=make([]string,0,len(f.throws))
  for cidr:=range f.throws{routes=append(routes,cidr)}
  sort.Strings(routes)
  for _,cidr:=range routes{lines=append(lines,"throw "+strings.TrimSuffix(cidr,"/32"))}
  return strings.Join(lines,"\n"),nil
 case reflect.DeepEqual(args,ruleShow()):
  lines:=[]string{"0: from all lookup local","32766: from all lookup main"}
  keys:=make([]int,0,len(f.rules))
  for id:=range f.rules{keys=append(keys,id)}
  sort.Ints(keys)
  for _,id:=range keys{
   lines=append(lines,fmt.Sprintf("%d: from all uidrange %s lookup %d",
    id,f.rules[id],Table))
  }
  return strings.Join(lines,"\n"),nil
 case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[3]=="throw":
  cidr:=args[4]
  if args[2]=="add"{
   if !f.defaultTun||f.throws[cidr]{return "",errors.New("throw occupied")}
   if cidr==f.failCIDR{return "",errors.New("injected direct route add failure")}
   f.throws[cidr]=true;return "",nil
  }
  if args[2]=="del"{
   if !f.throws[cidr]{return "",errors.New("foreign throw deletion")}
   delete(f.throws,cidr);return "",nil
  }
 case reflect.DeepEqual(args,routeAdd(f.tun)):
  if f.defaultTun{return "",errors.New("default route occupied")}
  f.defaultTun=true;return "",nil
 case reflect.DeepEqual(args,routeDel(f.tun)):
  if !f.defaultTun||len(f.throws)>0{return "",errors.New("default route or throw still occupied")}
  f.defaultTun=false;return "",nil
 case len(args)==9&&args[0]=="-4"&&args[1]=="rule"&&
  (args[2]=="add"||args[2]=="del"):
  pref,e:=strconv.Atoi(args[4]);if e!=nil{return "",e}
  uidrange:=args[6]
  if args[2]=="add"{
   if _,exists:=f.rules[pref];exists{return "",errors.New("UID priority occupied")}
   f.rules[pref]=uidrange;return "",nil
  }
  if f.rules[pref]!=uidrange{return "",errors.New("wrong UID rule deletion")}
  delete(f.rules,pref);return "",nil
 }
 return "",fmt.Errorf("unexpected Android root ip command: %s",key)
}
func b33Fake(t *testing.T)(*b33RouteKernel){
 t.Helper()
 return &b33RouteKernel{tun:"wbdv40",throws:map[string]bool{},rules:map[int]string{}}
}
func b33CheckedStop(t *testing.T,owner interface{Stop()error},f *b33RouteKernel,path string){
 t.Helper()
 if err:=owner.Stop();err!=nil{t.Fatal(err)}
 if f.defaultTun||len(f.throws)!=0||len(f.rules)!=0{t.Fatal("FIB/UID route leaked")}
 if _,e:=os.Stat(path);!os.IsNotExist(e){t.Fatal("durable route journal leaked")}
}
func b33Order(t *testing.T,f *b33RouteKernel){
 t.Helper()
 directAt,firstUID:=-1,-1
 for i,cmd:=range f.calls{
  if strings.Contains(cmd,"route add throw 192.168.7.0/24"){directAt=i}
  if strings.Contains(cmd,"rule add pref")&&firstUID<0{firstUID=i}
 }
 if directAt<0||firstUID<0||directAt>=firstUID{
  t.Fatalf("direct route was not effective before the first selected App UID rule: %d %d",directAt,firstUID)
 }
}
func TestB33OriginalRootSingleDirectCIDRKernelStop(t *testing.T){
 _,path,p:=fixture(t)
 p.ServerIP="203.0.113.9"
 p.DirectCIDRs=[]string{"192.168.7.0/24"}
 fake:=b33Fake(t)
 owner,e:=New(fake.run,path,p);if e!=nil{t.Fatal(e)}
 if !fake.throws["192.168.7.0/24"]||!fake.throws["203.0.113.9/32"]||len(fake.rules)!=1{
  t.Fatal("single UID native FIB bypass or rule absent")
 }
 b33Order(t,fake)
 b33CheckedStop(t,owner,fake,path)
}
func TestB33OriginalRootSelectedGroupDirectCIDRKernelStop(t *testing.T){
 _,path,p:=groupFixture(t)
 p.ServerIP="203.0.113.9"
 p.DirectCIDRs=[]string{"10.9.0.0/16","192.168.7.0/24"}
 fake:=b33Fake(t)
 owner,e:=NewGroup(fake.run,path,p);if e!=nil{t.Fatal(e)}
 if len(fake.throws)!=3||len(fake.rules)!=len(p.UIDs){t.Fatal("group real direct routes/UIDs missing")}
 b33Order(t,fake)
 b33CheckedStop(t,owner,fake,path)
}
func TestB33OriginalRootAllOrdinaryAppsDirectCIDRKernelStop(t *testing.T){
 _,path,p:=allFixture(t)
 p.DirectCIDRs=[]string{"10.9.0.0/16","192.168.7.0/24"}
 fake:=b33Fake(t)
 owner,e:=NewAllApps(fake.run,path,p);if e!=nil{t.Fatal(e)}
 if len(fake.throws)!=3||len(fake.rules)!=len(p.ranges()){t.Fatal("all-App direct routes/UIDs missing")}
 b33Order(t,fake)
 b33CheckedStop(t,owner,fake,path)
}
func TestB33OriginalRootDirectCIDRFailureRollsBack(t *testing.T){
 _,path,p:=groupFixture(t)
 p.ServerIP="203.0.113.9"
 p.DirectCIDRs=[]string{"10.9.0.0/16","192.168.7.0/24"}
 fake:=b33Fake(t);fake.failCIDR="192.168.7.0/24"
 if _,e:=NewGroup(fake.run,path,p);e==nil{t.Fatal("claimed a partial direct CIDR route")}
 if fake.defaultTun||len(fake.throws)!=0||len(fake.rules)!=0{t.Fatal("partial prefix route not rolled back")}
 if _,e:=os.Stat(path);!os.IsNotExist(e){t.Fatal("journal not cleared after verified rollback")}
}

func TestB58SixteenDirectPrefixesAndSixteenAppUIDsOriginalKernel(t *testing.T){
 _,path,plan:=groupFixture(t)
 plan.ServerIP="203.0.113.9"
 plan.UIDs=make([]int,16)
 for i:=range plan.UIDs{plan.UIDs[i]=11200+i}
 var direct []string
 for i:=0;i<16;i++{direct=append(direct,fmt.Sprintf("10.%d.0.0/16",i))}
 sort.Strings(direct)
 plan.DirectCIDRs=direct
 fake:=b33Fake(t)
 owner,err:=NewGroup(fake.run,path,plan)
 if err!=nil{t.Fatal(err)}
 if len(fake.throws)!=17||len(fake.rules)!=16{
  t.Fatalf("original FIB missing 16 CIDRs/16 UIDs: %d %d",
   len(fake.throws),len(fake.rules))
 }
 reads:=0
 for _,call:=range fake.calls{
  if strings.Contains(call," route show table ")||
   strings.Contains(call," rule show"){reads++}
 }
 if reads>14{t.Fatalf("still rereads FIB per UID/CIDR: %d",reads)}
 b33CheckedStop(t,owner,fake,path)
}
func TestB58AllAppsSixteenDirectPrefixesSingleFIB(t *testing.T){
 _,path,plan:=allFixture(t)
 var direct []string
 for i:=0;i<16;i++{direct=append(direct,fmt.Sprintf("10.%d.0.0/16",i))}
 sort.Strings(direct)
 plan.DirectCIDRs=direct
 fake:=b33Fake(t)
 owner,err:=NewAllApps(fake.run,path,plan)
 if err!=nil{t.Fatal(err)}
 if len(fake.throws)!=17||len(fake.rules)!=len(plan.ranges()){
  t.Fatalf("ordinary app FIB incomplete: %d prefixes %d UID rules",
   len(fake.throws),len(fake.rules))
 }
 reads:=0
 for _,call:=range fake.calls{
  if strings.Contains(call," route show table ")||
   strings.Contains(call," rule show"){reads++}
 }
 if reads>14{t.Fatalf("full-app startup still quadratic: %d",reads)}
 b33CheckedStop(t,owner,fake,path)
}
