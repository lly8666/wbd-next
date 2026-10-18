package realityfront

import (
    "errors"
    "sync"
    "testing"
    "time"
)

type f2RuntimeFake struct {
    mu sync.Mutex
    epoch [16]byte
    staged []FecV2Intent
    ack FecV2Ack
    observeError bool
    stageError bool
    stageEntered chan struct{}
    stageRelease chan struct{}
}
func (f *f2RuntimeFake) Observe(epoch [16]byte,client string,dir FecV2Direction,now time.Duration)(FecV2Snapshot,error){
    if epoch!=f.epoch{return FecV2Snapshot{},ErrFecV2Scope}
    if f.observeError{return FecV2Snapshot{},errors.New("no mature source")}
    return FecV2Snapshot{Client:client,Direction:dir,At:now,Validity:FecV2Unknown},nil
}
func (f *f2RuntimeFake) Stage(epoch [16]byte,v FecV2Intent) error{
    if epoch!=f.epoch{return ErrFecV2Scope}
    if f.stageError{return errors.New("original Rust declined stage")}
    if f.stageEntered!=nil{
        select{case f.stageEntered<-struct{}{}:default:}
        <-f.stageRelease
    }
    f.mu.Lock()
    f.staged=append(f.staged,v)
    f.mu.Unlock()
    return nil
}
func (f *f2RuntimeFake) Readback(epoch [16]byte,client string,dir FecV2Direction)(FecV2Ack,error){
    if epoch!=f.epoch{return FecV2Ack{},ErrFecV2Scope}
    if f.ack.Client==""{return FecV2Ack{},errors.New("no original applied receipt")}
    return f.ack,nil
}

func TestF2ControlRuntimeAutoCadenceUnknownAndOriginalAppliedAck(t *testing.T){
    var epoch [16]byte
    epoch[0]=71
    cfg:=f2Config("original-peer",FecV2S2C,FecV2Auto,FecV2Conservative)
    backend:=&f2RuntimeFake{epoch:epoch,observeError:true}
    run,err:=newFecV2ControlRuntime(cfg,epoch,backend)
    if err!=nil{t.Fatal(err)}
    if fecV2RuntimeCadence!=2*time.Second{t.Fatal("not a real 2s cadence")}
    if err:=run.Tick(time.Second);err!=nil{t.Fatal(err)}
    state,e:=run.Snapshot()
    if e!=nil||!state.Initialized||state.RequestedRevision==0||len(backend.staged)!=1{
        t.Fatalf("original Go first config not staged %+v err=%v",state,e)
    }
    wanted:=backend.staged[0]
    // No Rust applied receipt: requested is NOT applied and UNKNOWN
    // must not cause another SetTxFec or infer zero loss.
    if err:=run.Tick(3*time.Second);err!=nil{t.Fatal(err)}
    state,_=run.Snapshot()
    if state.AppliedRevision!=0||len(backend.staged)!=1{
        t.Fatalf("UNKNOWN created new policy or fake ACK %+v",state)
    }
    // Invalid foreign ACK must be fail-closed; a matching original Rust
    // revision/profile may update only this exact client/direction.
    backend.ack=FecV2Ack{Client:"foreign",Direction:cfg.Direction,
        Revision:wanted.Revision,Profile:wanted.Profile,Applied:true}
    if err:=run.Tick(5*time.Second);!errors.Is(err,ErrFecV2Scope){
        t.Fatalf("cross-client applied ACK accepted: %v",err)
    }
    backend.ack=FecV2Ack{Client:cfg.Client,Direction:cfg.Direction,
        Revision:wanted.Revision,Profile:wanted.Profile,Applied:true}
    if err:=run.Tick(7*time.Second);err!=nil{t.Fatal(err)}
    state,_=run.Snapshot()
    if state.AppliedRevision!=wanted.Revision||state.AppliedProfile!=wanted.Profile{
        t.Fatalf("original applied proof not reflected %+v",state)
    }
    run.Stop()
    if err:=run.Tick(9*time.Second);!errors.Is(err,errFecV2RuntimeStopped){
        t.Fatalf("late write after Stop: %v",err)
    }
    if len(backend.staged)!=1{t.Fatal("Stop leaked a late policy write")}
}

func TestF2ControlRuntimeStopJoinsBlockedOriginalStage(t *testing.T){
    var epoch [16]byte
    epoch[0]=4
    cfg:=f2Config("protected-owner",FecV2S2C,FecV2Auto,FecV2Aggressive)
    fake:=&f2RuntimeFake{
        epoch:epoch,
        stageEntered:make(chan struct{},1),
        stageRelease:make(chan struct{}),
    }
    run,err:=newFecV2ControlRuntime(cfg,epoch,fake)
    if err!=nil{t.Fatal(err)}
    tickDone:=make(chan error,1)
    go func(){tickDone<-run.Tick(time.Second)}()
    select{
    case <-fake.stageEntered:
    case <-time.After(time.Second):t.Fatal("original stage not entered")
    }
    stopped:=make(chan struct{})
    go func(){run.Stop();close(stopped)}()
    select{
    case <-stopped:t.Fatal("Stop returned while original stage held")
    case <-time.After(15*time.Millisecond):
    }
    close(fake.stageRelease)
    if err:=<-tickDone;err!=nil{t.Fatal(err)}
    select{
    case <-stopped:
    case <-time.After(time.Second):t.Fatal("Stop did not join original stage")
    }
    if err:=run.Tick(3*time.Second);!errors.Is(err,errFecV2RuntimeStopped){
        t.Fatalf("late stage accepted: %v",err)
    }
    fake.mu.Lock()
    stages:=len(fake.staged)
    fake.mu.Unlock()
    if stages!=1{t.Fatalf("Stop lifetime staged %d times",stages)}
    if _,err:=newFecV2ControlRuntime(cfg,[16]byte{},fake);err==nil{
        t.Fatal("zero authenticated epoch accepted")
    }
    if err:=run.Start();!errors.Is(err,errFecV2RuntimeStopped){
        t.Fatal("stopped owner restarted")
    }
}


// A GUI/CLI revision is not a string toggle. It must be scoped to the
// authenticated client, direction AND epoch; the requested revision is
// committed only when the real backend accepted the intent. Readback is a
// separate operation; OFF cannot be advertised until Rust implements it.
func TestF2ControlOperatorFixedAutoRevisionScopeAndFailClosedOff(t *testing.T){
    var epoch [16]byte
    epoch[0]=9
    cfg:=f2Config("protected-owner",FecV2S2C,FecV2Auto,FecV2Conservative)
    backend:=&f2RuntimeFake{epoch:epoch,observeError:true}
    r,err:=newFecV2ControlRuntime(cfg,epoch,backend)
    if err!=nil{t.Fatal(err)}
    if e:=r.Tick(time.Second);e!=nil{t.Fatal(e)}
    first,_:=r.Snapshot()
    if first.RequestedRevision!=1||first.AppliedRevision!=0{t.Fatalf("first stage %+v",first)}
    fixed:=cfg
    fixed.Mode=FecV2Fixed
    fixed.Profile=FecV2High
    fixed.ConfigRevision=2
    wrong:=epoch
    wrong[0]=10
    if _,e:=r.ApplyOperatorConfig(wrong,fixed,2*time.Second);!errors.Is(e,ErrFecV2Scope){
        t.Fatalf("wrong TLS epoch changed policy: %v",e)
    }
    backend.stageError=true
    if _,e:=r.ApplyOperatorConfig(epoch,fixed,2*time.Second);e==nil{
        t.Fatal("backend refusal acknowledged as requested")
    }
    state,_:=r.Snapshot()
    if state.RequestedRevision!=1||len(backend.staged)!=1{
        t.Fatalf("failed native stage advanced Go revision %+v",state)
    }
    backend.stageError=false
    state,err=r.ApplyOperatorConfig(epoch,fixed,3*time.Second)
    if err!=nil||state.RequestedRevision!=2||state.Desired!=FecV2High||
        state.AppliedRevision!=0||len(backend.staged)!=2{
        t.Fatalf("fixed config did not stage without fabricated ACK %+v %v",state,err)
    }
    if _,e:=r.ApplyOperatorConfig(epoch,fixed,4*time.Second);!errors.Is(e,ErrFecV2Revision){
        t.Fatalf("duplicate config revision accepted: %v",e)
    }
    foreign:=fixed
    foreign.Client="another-user"
    foreign.ConfigRevision=3
    if _,e:=r.ApplyOperatorConfig(epoch,foreign,4*time.Second);!errors.Is(e,ErrFecV2Scope){
        t.Fatalf("cross-client revision accepted: %v",e)
    }
    off:=fixed
    off.Mode=FecV2Off
    off.ConfigRevision=3
    if _,e:=r.ApplyOperatorConfig(epoch,off,4*time.Second);!errors.Is(e,errFecV2RuntimeOffUnwired){
        t.Fatalf("unwired OFF was treated applied: %v",e)
    }
    if e:=r.Tick(5*time.Second);e!=nil{t.Fatal(e)}
    state,_=r.Snapshot()
    if state.AppliedRevision!=0||state.RequestedRevision!=2{
        t.Fatalf("no original Rust ACK rewrote Go UI %+v",state)
    }
    backend.ack=FecV2Ack{Client:cfg.Client,Direction:cfg.Direction,
        Revision:2,Profile:FecV2High,Applied:true}
    if e:=r.Tick(7*time.Second);e!=nil{t.Fatal(e)}
    state,_=r.Snapshot()
    if state.AppliedRevision!=2||state.AppliedProfile!=FecV2High||
        len(backend.staged)!=2{
        t.Fatalf("Rust applied fixed receipt was not reflected %+v",state)
    }
    r.Stop()
    if _,e:=r.ApplyOperatorConfig(epoch,off,8*time.Second);!errors.Is(e,errFecV2RuntimeStopped){
        t.Fatalf("Stop permitted late GUI config %v",e)
    }
}
