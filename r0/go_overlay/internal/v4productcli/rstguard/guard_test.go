package rstguard

import (
    "errors"
    "fmt"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

type fakeIPTables struct{
    present bool
    failInsert bool
    failList bool
    failDelete bool
    extra bool
    packets uint64
    plan Plan
}
func (f *fakeIPTables) run(args ...string)(string,error){
    if len(args)<6 || args[0]!="-w" || args[2]!="-t" ||
        args[3]!="filter" || args[5]!="OUTPUT"{return "",errors.New("not scoped")}
    switch args[4]{
    case "-S":
        if f.failList{return "",errors.New("list unavailable")}
        if !f.present{return "-P OUTPUT ACCEPT\n",nil}
        line:="-A OUTPUT "+strings.Join(f.plan.params()," ")+"\n"
        if f.extra{line+=line}
        return "-P OUTPUT ACCEPT\n"+line,nil
    case "-C":
        if !f.present||strings.Join(args[6:]," ")!=strings.Join(f.plan.params()," "){
            return "",errors.New("not matching")
        }
        return "",nil
    case "-I":
        if f.failInsert{return "",errors.New("insert failed")}
        if f.present{return "",errors.New("already present")}
        f.present=true;f.plan=parseTestPlan(args)
        return "",nil
    case "-D":
        if f.failDelete || !f.present || strings.Join(args[6:]," ")!=strings.Join(f.plan.params()," "){
            return "",errors.New("delete failed")
        }
        f.present=false
        return "",nil
    case "-n":
        // -w 2 -t filter -n -v -x -L OUTPUT
        if len(args)!=9||args[7]!="-L"{return "",errors.New("invalid counter call")}
        if !f.present{return "",nil}
        return fmt.Sprintf("pkts bytes target prot opt in out source destination\n%d 100 DROP tcp -- * wlan0 0/0 0/0 tcp flags:0x04/0x04 /* %s */\n",f.packets,marker),nil
    }
    return "",errors.New("unknown operation")
}
func parseTestPlan(args []string) Plan{
    p:=Plan{Version:1}
    for i:=6;i+1<len(args);i++{
        switch args[i]{
        case "-o":p.Interface=args[i+1]
        case "-s":p.SourceIP=strings.TrimSuffix(args[i+1],"/32")
        case "-d":p.PeerIP=strings.TrimSuffix(args[i+1],"/32")
        case "--sport":fmt.Sscan(args[i+1],&p.SourcePort)
        case "--dport":fmt.Sscan(args[i+1],&p.PeerPort)
        }
    }
    return p
}
func basePlan()Plan{return Plan{Version:1,Interface:"wlan0",SourceIP:"192.0.2.5",
PeerIP:"198.51.100.2",SourcePort:45821,PeerPort:443}}
func TestScopedRSTGuardOwnedInstallCounterAndStop(t *testing.T){
    f:=&fakeIPTables{packets:3}
    journal:=filepath.Join(t.TempDir(),"rst-guard.json")
    g,recovered,e:=New(f.run,journal,basePlan())
    if e!=nil||recovered||!f.present{t.Fatalf("install/lock: %v",e)}
    if n,ok:=g.DropCounter();!ok||n!=3{t.Fatalf("counter=%d known=%v",n,ok)}
    if e=g.Close();e!=nil||f.present{t.Fatalf("stop: %v",e)}
    if _,e=os.Lstat(journal);!errors.Is(e,os.ErrNotExist){t.Fatal("journal not retired")}
}
func TestScopedRSTGuardCrashRecoveryAcrossNewFlow(t *testing.T){
    f:=&fakeIPTables{}
    path:=filepath.Join(t.TempDir(),"rst-guard.json")
    g,_,e:=New(f.run,path,basePlan());if e!=nil{t.Fatal(e)}
    if e=g.lock.Close();e!=nil{t.Fatal(e)} // simulated process crash; no kernel mutation here
    next:=basePlan();next.SourcePort++
    g2,recovered,e:=New(f.run,path,next)
    if e!=nil||!recovered||f.plan.SourcePort!=next.SourcePort{t.Fatalf("crash recovery: %v",e)}
    if e=g2.Close();e!=nil||f.present{t.Fatalf("post recovery stop: %v",e)}
}
func TestScopedRSTGuardFailClosedForeignAndDuplicates(t *testing.T){
    p:=basePlan()
    for _,tc:=range []struct{name string;extra bool;different bool}{
        {"foreign",false,true},{"duplicate",true,false},
    }{
        t.Run(tc.name,func(t *testing.T){
            f:=&fakeIPTables{present:true,extra:tc.extra,plan:p}
            if tc.different{f.plan.SourcePort++}
            path:=filepath.Join(t.TempDir(),"rst-guard.json")
            if _,_,e:=New(f.run,path,p);!errors.Is(e,ErrScope){t.Fatalf("must refuse foreign %v",e)}
            if !f.present{t.Fatal("foreign rule wrongly deleted")}
        })
    }
}
func TestScopedRSTGuardInstallFailureAndJournalSafety(t *testing.T){
    f:=&fakeIPTables{failInsert:true}
    dir:=t.TempDir()
    path:=filepath.Join(dir,"rst-guard.json")
    if _,_,e:=New(f.run,path,basePlan());!errors.Is(e,ErrBackend){t.Fatalf("insert failure: %v",e)}
    if f.present{t.Fatal("fail closed no residual rule")}
    if _,e:=os.Stat(path);!errors.Is(e,os.ErrNotExist){t.Fatal("journal not retired")}
    if e:=os.WriteFile(path,[]byte("foreign"),0600);e!=nil{t.Fatal(e)}
    if _,_,e:=New(f.run,path,basePlan());!errors.Is(e,ErrJournal){t.Fatal("foreign journal accepted")}
}
func TestScopedRSTGuardConcurrentLockAndUncertainStop(t *testing.T){
    f:=&fakeIPTables{}
    path:=filepath.Join(t.TempDir(),"rst-guard.json")
    g,_,e:=New(f.run,path,basePlan());if e!=nil{t.Fatal(e)}
    if _,_,e:=New(f.run,path,basePlan());!errors.Is(e,ErrLocked){t.Fatalf("lock bypass: %v",e)}
    f.failDelete=true
    if e=g.Close();!errors.Is(e,ErrCleanup){t.Fatalf("STOP must fail: %v",e)}
    if _,e:=os.Stat(path);e!=nil{t.Fatal("uncertain Stop lost recovery journal")}
    f.failDelete=false
    recovered,yes,e:=New(f.run,path,basePlan())
    if e!=nil||!yes{t.Fatalf("subsequent exact recovery: %v",e)}
    if e=recovered.Close();e!=nil{t.Fatal(e)}
}
func TestScopedRSTGuardRejectNonPhysicalScope(t *testing.T){
    for _,p:=range []Plan{
        {Version:1,Interface:"wlan0",SourceIP:"127.0.0.1",PeerIP:"198.51.100.2",SourcePort:45444,PeerPort:443},
        {Version:1,Interface:"wlan0;exit",SourceIP:"192.0.2.5",PeerIP:"198.51.100.2",SourcePort:45444,PeerPort:443},
        {Version:1,Interface:"wlan0",SourceIP:"192.0.2.5",PeerIP:"::1",SourcePort:45444,PeerPort:443},
    }{
        if p.valid(){t.Fatalf("accepted invalid scope")}
    }
}
