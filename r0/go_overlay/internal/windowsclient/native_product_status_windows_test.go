//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "os"
    "path/filepath"
    "testing"
)

func TestPLAN010NativeReadOnlyDiskStatusAndConflict(t *testing.T){
    ctx:=context.Background()
    state:=filepath.Join(t.TempDir(),"native-network-state.json")
    read:=func(want string)N4NativeStateSnapshot{
        t.Helper()
        snap,err:=N4NativeInspectState(ctx,state)
        if err!=nil{t.Fatal(err)}
        if snap.State!=want||snap.Schema!=N4NativeStateSchema||snap.GuardQualified{
            t.Fatalf("read-only report cannot authorize real native WFP: %+v",snap)
        }
        return snap
    }
    if snap:=read("absent");snap.LegacyJournal||snap.NativeWAL||snap.RouteIntent {t.Fatal(snap)}
    if _,err:=os.Stat(state);!errors.Is(err,os.ErrNotExist){t.Fatal("read-only scan wrote state",err)}
    if err:=os.WriteFile(state,[]byte("old shell journal"),0600);err!=nil{t.Fatal(err)}
    if snap:=read("legacy_journal");!snap.LegacyJournal||snap.NativeWAL {t.Fatal(snap)}
    if err:=os.Remove(state);err!=nil{t.Fatal(err)}
    orphan:=state+".n4-owned-wal.routes"
    old:=[]byte("unconfirmed route intent")
    if err:=os.WriteFile(orphan,old,0600);err!=nil{t.Fatal(err)}
    if snap:=read("orphan_route_intent");!snap.RouteIntent||snap.NativeWAL {t.Fatal(snap)}
    if bytes,err:=os.ReadFile(orphan);err!=nil||string(bytes)!=string(old){
        t.Fatalf("read-only scan changed route intent: %v",err)
    }
    if err:=os.Remove(orphan);err!=nil{t.Fatal(err)}
    wal:=state+".n4-owned-wal"
    malformed:=[]byte(`{"schema":"foreign","identity":"spoof"}`)
    if err:=os.WriteFile(wal,malformed,0600);err!=nil{t.Fatal(err)}
    snap,err:=N4NativeInspectState(ctx,state)
    if !errors.Is(err,ErrN4JournalConflict)||snap.State!="invalid_native_wal"{
        t.Fatalf("untrusted WAL falsely trusted: %+v err=%v",snap,err)
    }
    if err:=os.Remove(wal);err!=nil{t.Fatal(err)}
    id:=N4UnifiedIdentity{
        Installation:[16]byte{1},Generation:[16]byte{2},
        WintunLUID:100,WintunIndex:8,
    }
    record:=n4UnifiedJournal{Identity:id,Phase:"applying"}
    if err:=n4UnifiedWrite(wal,record,true);err!=nil{t.Fatal(err)}
    if snap:=read("native_wal_unverified");!snap.NativeWAL||snap.Phase!="applying"||snap.RecordCount!=0||snap.GuardQualified{
        t.Fatalf("disk WAL incorrectly promoted to network-ready: %+v",snap)
    }
    if err:=os.WriteFile(state,[]byte("legacy"),0600);err!=nil{t.Fatal(err)}
    snap,err=N4NativeInspectState(ctx,state)
    if !errors.Is(err,ErrN4JournalConflict)||snap.State!="conflict"{
        t.Fatalf("two different owners must never be trusted: %+v %v",snap,err)
    }
    if err:=os.Remove(state);err!=nil{t.Fatal(err)}
    if err:=os.Remove(wal);err!=nil{t.Fatal(err)}
    if err:=os.Mkdir(wal,0700);err!=nil{t.Fatal(err)}
    if _,err:=N4NativeInspectState(ctx,state);!errors.Is(err,ErrN4JournalConflict){
        t.Fatalf("directory masqueraded as owned WAL: %v",err)
    }
    cancelCtx,cancel:=context.WithCancel(ctx)
    cancel()
    if _,err:=N4NativeInspectState(cancelCtx,state);!errors.Is(err,context.Canceled){t.Fatal(err)}
    if _,err:=N4NativeInspectState(ctx,"relative.json");!errors.Is(err,ErrNetworkPlan){t.Fatal(err)}
    if _,err:=N4NativeInspectState(nil,state);!errors.Is(err,ErrNetworkPlan){t.Fatal(err)}
}
