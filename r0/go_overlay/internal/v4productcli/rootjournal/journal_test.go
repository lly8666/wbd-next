package rootjournal

import(
    "errors"
    "fmt"
    "os"
    "path/filepath"
    "reflect"
    "strings"
    "testing"
)

type fakeIP struct{
    tun string
    uid int
    route bool
    rule bool
    peerThrow string
    foreign string
    refuse string
    calls [][]string
}
func (f *fakeIP) run(args ...string)(string,error){
    f.calls=append(f.calls,append([]string(nil),args...))
    key:=strings.Join(args," ")
    if strings.Contains(key,f.refuse)&&f.refuse!=""{
        return "",errors.New("simulated Android kernel mutation refused")
    }
    switch{
    case reflect.DeepEqual(args,routeShow()):
        if f.foreign=="route"{return "default dev other0\n",nil}
        out:=""
        if f.route{out+="default dev "+f.tun+" scope link\n"}
        if f.peerThrow!=""{out+="throw "+f.peerThrow+"\n"}
        return out,nil
    case reflect.DeepEqual(args,ruleShow()):
        if f.foreign=="rule"{return fmt.Sprintf("%d: from all uidrange 10001-10001 lookup %d\n",Priority,Table),nil}
        if f.rule{
            return fmt.Sprintf("0: from all lookup local\n%d: from all uidrange %d-%d lookup %d\n",
                Priority,f.uid,f.uid,Table),nil
        }
        return "0: from all lookup local\n32766: from all lookup main\n",nil
    case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[2]=="add"&&args[3]=="throw":
        if f.peerThrow!=""||!f.route{return "",errors.New("peer throw occupied")}
        f.peerThrow=strings.TrimSuffix(args[4],"/32");return "",nil
    case len(args)==7&&args[0]=="-4"&&args[1]=="route"&&args[2]=="del"&&args[3]=="throw":
        if f.peerThrow!=strings.TrimSuffix(args[4],"/32"){return "",errors.New("peer exception foreign")}
        f.peerThrow="";return "",nil
    case len(args)>2&&args[0]=="-4"&&args[1]=="route"&&args[2]=="add":
        if f.route{return "",errors.New("File exists")}
        f.route=true;return "",nil
    case len(args)>2&&args[0]=="-4"&&args[1]=="route"&&args[2]=="del":
        if !f.route||f.peerThrow!=""{return "",errors.New("route missing or peer active")}
        f.route=false;return "",nil
    case len(args)>2&&args[0]=="-4"&&args[1]=="rule"&&args[2]=="add":
        if f.rule{return "",errors.New("File exists")}
        f.rule=true;return "",nil
    case len(args)>2&&args[0]=="-4"&&args[1]=="rule"&&args[2]=="del":
        if !f.rule{return "",errors.New("no owned rule")}
        f.rule=false;return "",nil
    default:
        return "",fmt.Errorf("unknown ip invocation: %q",key)
    }
}
func fixture(t *testing.T)(*fakeIP,string,Plan){
    t.Helper()
    dir:=filepath.Join(t.TempDir(),"only-root")
    path:=filepath.Join(dir,"route-journal.json")
    p:=Plan{UID:11234,Tun:"wbdv40",Lease:"10.66.0.8/32",
        Underlay:"wlan0",IfIndex:27,NetworkHandle:135}
    return &fakeIP{tun:p.Tun,uid:p.UID},path,p
}
func TestAuthenticatedOneUIDTransactionBeforeStopExact(t *testing.T){
    f,path,p:=fixture(t)
    s,err:=New(f.run,path,p)
    if err!=nil{t.Fatal(err)}
    if !f.route||!f.rule{t.Fatal("no kernel route/rule installed")}
    st,err:=os.Stat(path)
    if err!=nil||st.Mode().Perm()!=0600{t.Fatal("journal not private",err)}
    if err=s.Stop();err!=nil{t.Fatal(err)}
    if f.rule||f.route{t.Fatal("kernel WBD state leaked")}
    if err=s.Stop();err!=nil{t.Fatal("Stop not idempotent",err)}
    if _,err=os.Stat(path);!os.IsNotExist(err){t.Fatal("journal not removed",err)}
    for _,cmd:=range f.calls{
        k:=strings.Join(cmd," ")
        if strings.Contains(k,"main")||strings.Contains(k,"sysctl")||
           strings.Contains(k,"iptables")||strings.Contains(k,"global"){
            t.Fatal("unexpected global mutation",k)
        }
    }
}
func TestCrashBeforeAndAfterRootRuleUsesDurableRecovery(t *testing.T){
    for _,stage:=range []string{"route-only","ready","journal-only"}{
        t.Run(stage,func(t *testing.T){
            f,path,p:=fixture(t)
            s,err:=New(f.run,path,p)
            if err!=nil{t.Fatal(err)}
            if stage=="route-only"{f.rule=false}
            if stage=="journal-only"{f.rule=false;f.route=false}
            // The genuine cross-process lock refuses overlapping owners.
            if _,err:=New(f.run,path,p);err==nil{
                t.Fatal("second root process stole a still-live kernel route")
            }
            // Simulate process death (flock auto-released by kernel);
            // do not call old Stop or remove any route/journal.
            if err=s.lock.Close();err!=nil{t.Fatal(err)}
            s.active=false;s.lock=nil
            resumed,err:=New(f.run,path,p)
            if err!=nil{t.Fatal("failed to recover exactly owned state",err)}
            if !f.rule||!f.route{t.Fatal("new generation not installed")}
            if err=resumed.Stop();err!=nil{t.Fatal(err)}
            if err=s.Stop();err!=nil{t.Fatal(err)}
        })
    }
}
func TestForeignPriorityTableOrJournalFailClosed(t *testing.T){
    for _,foreign:=range []string{"route","rule"}{
        t.Run(foreign,func(t *testing.T){
            f,path,p:=fixture(t);f.foreign=foreign
            if _,err:=New(f.run,path,p);err==nil{t.Fatal("accepted foreign kernel state")}
            if f.route||f.rule{t.Fatal("mutated foreign state")}
        })
    }
    f,path,p:=fixture(t)
    if err:=os.Mkdir(filepath.Dir(path),0700);err!=nil{t.Fatal(err)}
    if err:=os.WriteFile(path,[]byte("foreign"),0600);err!=nil{t.Fatal(err)}
    if _,err:=New(f.run,path,p);err==nil{t.Fatal("accepted forged journal")}
}
func TestPartialRuleFailureDoesNotPublishReadyOrLeak(t *testing.T){
    f,path,p:=fixture(t);f.refuse="rule add"
    if _,err:=New(f.run,path,p);err==nil{t.Fatal("claimed route readiness")}
    if f.route||f.rule{t.Fatal("no rollback")}
    if _,err:=os.Stat(path);!os.IsNotExist(err){
        t.Fatal("journal not removed after proven rollback",err)
    }
}
func TestRefuseUIDRootAndNon32UntrustedLease(t *testing.T){
    f,path,p:=fixture(t);p.UID=0
    if _,err:=New(f.run,path,p);err==nil{t.Fatal("root process policy would route its own FakeTCP")}
    p.UID=11234;p.Lease="10.66.0.0/24"
    if _,err:=New(f.run,path,p);err==nil{t.Fatal("unauthenticated broad lease")}
    p.Lease="10.66.0.8/32";p.NetworkHandle=0
    if _,err:=New(f.run,path,p);err==nil{t.Fatal("unselected Android Network")}
}

// B31: selected UID original server-IP bypass is installed before the UID
// policy rule, and is removed with the original root journal owner.
func TestB31SingleUIDServerPeerThrowBeforeRuleAndStop(t *testing.T){
 f,path,plan:=fixture(t);plan.ServerIP="203.0.113.9"
 s,err:=New(f.run,path,plan);if err!=nil{t.Fatal(err)}
 if !f.route||!f.rule||f.peerThrow!=plan.ServerIP{t.Fatal("missing real peer bypass")}
 throwAt,ruleAt:=-1,-1
 for i,cmd:=range f.calls{
  line:=strings.Join(cmd," ")
  if strings.Contains(line,"route add throw 203.0.113.9/32"){throwAt=i}
  if strings.Contains(line,"rule add pref"){ruleAt=i}
 }
 if throwAt<0||ruleAt<0||throwAt>=ruleAt{t.Fatal("peer exclusion came after first App UID")}
 if err=s.Stop();err!=nil{t.Fatal(err)}
 if f.route||f.rule||f.peerThrow!=""{t.Fatal("owned peer or UID route leaked")}
}
func TestB31SingleUIDPeerFailureRollsBackRoute(t *testing.T){
 f,path,plan:=fixture(t);plan.ServerIP="203.0.113.9";f.refuse="route add throw"
 if _,err:=New(f.run,path,plan);err==nil{t.Fatal("accepted failed peer exclusion")}
 if f.route||f.rule||f.peerThrow!=""{t.Fatal("partial root route leaked")}
 if _,err:=os.Stat(path);!os.IsNotExist(err){t.Fatal("journal retained after proven rollback")}
}
