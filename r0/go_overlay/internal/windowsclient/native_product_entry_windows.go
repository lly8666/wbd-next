//go:build windows

package windowsclient

// PLAN-010: original Windows product CLI entry points. Neither an old
// PowerShell journal nor unverified host-wide WFP gets a fallback executor.
import (
    "context"
    "errors"
    "fmt"
    "os"
    "path/filepath"
    "strings"
)

// N4NativeNetworkReady is the product admission barrier. Never promote the
// donor's assemblyOnly transaction by a command-line flag: production WFP
// installation is still refused in native_wfp_guard_windows.go until its
// real owner/OS policy checks have independent native evidence.
func N4NativeNetworkReady(ctx context.Context) error {
    if ctx==nil {return ErrNetworkPlan}
    if err:=ctx.Err();err!=nil{return err}
    return fmt.Errorf("%w: production native WFP Apply and authenticated Stop have not been qualified", ErrN4NativeGuard)
}

// N4NativeRecoverState is invoked only by the same original Go executable
// used for Connect and Stop. It does not spawn any network management tools.
// A v1 shell journal is NEVER interpreted as an owned native v4 WAL.
func N4NativeRecoverState(ctx context.Context, statePath string) error {
    if ctx==nil{return ErrNetworkPlan}
    if err:=ctx.Err();err!=nil{return err}
    if strings.TrimSpace(statePath)=="" || !filepath.IsAbs(statePath){
        return ErrNetworkPlan
    }
    old,err:=os.Lstat(statePath)
    switch {
    case err==nil:
        if old.Mode()&os.ModeSymlink!=0 || !old.Mode().IsRegular(){
            return ErrN4JournalConflict
        }
        return fmt.Errorf("%w: legacy script-owned network state must be recovered by the original version; native fallback is prohibited", ErrN4JournalConflict)
    case !errors.Is(err,os.ErrNotExist):
        return err
    }
    nativePath:=statePath+".n4-owned-wal"
    info,err:=os.Lstat(nativePath)
    if errors.Is(err,os.ErrNotExist){return nil}
    if err!=nil{return err}
    if info.Mode()&os.ModeSymlink!=0 || !info.Mode().IsRegular(){
        return ErrN4JournalConflict
    }
    journal,err:=n4UnifiedRead(nativePath)
    if err!=nil{return err}
    // Actual recovery uses the original pinned Wintun identity, durable
    // WFP guard and machine gate. Unsupported phases/ghost MTU stay errors
    // and the original WAL remains on disk for operator recovery.
    return N4WindowsRecoverPersistedPreRouteWAL(ctx,nativePath,journal.Identity)
}
