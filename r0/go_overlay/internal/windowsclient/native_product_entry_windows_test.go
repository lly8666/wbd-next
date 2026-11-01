//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "os"
    "path/filepath"
    "testing"
)
func TestPLAN010OriginalNativeRecoveryNoShellOrLegacyFallback(t *testing.T) {
    dir:=t.TempDir()
    path:=filepath.Join(dir,"network-state.json")
    if err:=N4NativeRecoverState(context.Background(),path);err!=nil{
        t.Fatalf("absent native and old state should be a verified no-op: %v",err)
    }
    // Partial route receipt without a primary WAL is NOT "nothing to do".
    orphan:=path+".n4-owned-wal.routes"
    if err:=os.WriteFile(orphan,[]byte("owned-intent"),0600);err!=nil{t.Fatal(err)}
    if err:=N4NativeRecoverState(context.Background(),path);!errors.Is(err,ErrN4JournalConflict){
        t.Fatalf("orphaned route journal falsely cleared: %v",err)
    }
    if _,err:=os.Stat(orphan);err!=nil{t.Fatal("orphan sidecar removed",err)}
    if err:=os.Remove(orphan);err!=nil{t.Fatal(err)}
    old:=[]byte(`{"schema":1,"foreign_or_legacy":true}`)
    if err:=os.WriteFile(path,old,0600);err!=nil{t.Fatal(err)}
    err:=N4NativeRecoverState(context.Background(),path)
    if !errors.Is(err,ErrN4JournalConflict){t.Fatalf("old shell journal used as native: %v",err)}
    got,err:=os.ReadFile(path);if err!=nil||string(got)!=string(old){t.Fatal("legacy state lost",err)}
    if err:=os.Remove(path);err!=nil{t.Fatal(err)}
    native:=path+".n4-owned-wal"
    malformed:=[]byte(`{"schema":777,"identity":"pretend-owned"}`)
    if err:=os.WriteFile(native,malformed,0600);err!=nil{t.Fatal(err)}
    if err:=N4NativeRecoverState(context.Background(),path);err==nil{
        t.Fatal("unowned native WAL recovered or erased")
    }
    got,err=os.ReadFile(native);if err!=nil||string(got)!=string(malformed){t.Fatal("unowned WAL lost",err)}
    ctx,cancel:=context.WithCancel(context.Background());cancel()
    if err:=N4NativeRecoverState(ctx,path);!errors.Is(err,context.Canceled){t.Fatal(err)}
    if err:=N4NativeNetworkReady(ctx);!errors.Is(err,context.Canceled){t.Fatal(err)}
    if err:=N4NativeNetworkReady(context.Background());!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("unverified native WFP product unexpectedly enabled: %v",err)
    }
    if err:=N4NativeRecoverState(context.Background(),"relative.json");!errors.Is(err,ErrNetworkPlan){t.Fatal(err)}
}
