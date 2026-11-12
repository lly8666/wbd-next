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
// v2 assemblyOnly transaction by a command-line flag; old WFP is not a new-session dependency.
// Actual four-stage Win32 and signed Wintun Rust/Stop require independent evidence.
func N4NativeNetworkReady(ctx context.Context) error {
    if ctx==nil {return ErrNetworkPlan}
    if err:=ctx.Err();err!=nil{return err}
    return fmt.Errorf("%w: no-WFP four-stage Win32 Apply, Rust ingress and authenticated Stop have not been qualified", ErrN4NativeGuard)
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
    if errors.Is(err,os.ErrNotExist){
        // A crash may strand a route sidecar even if the primary WAL was
        // lost. Do not display "recovered" while any owned route intent
        // remains on disk without a verifiable journal.
        for _,candidate:=range []string{nativePath+".routes",statePath+".routes"} {
            _,sideErr:=os.Lstat(candidate)
            if sideErr==nil{return fmt.Errorf("%w: orphan route sidecar without owned WAL: %s",ErrN4JournalConflict,candidate)}
            if !errors.Is(sideErr,os.ErrNotExist){return sideErr}
        }
        return nil
    }
    if err!=nil{return err}
    if info.Mode()&os.ModeSymlink!=0 || !info.Mode().IsRegular(){
        return ErrN4JournalConflict
    }
    journal,err:=n4UnifiedRead(nativePath)
    if err!=nil{return err}
    // A v2 WAL never has an old WFP guard. Never hand it to the legacy v1
    // guard recovery constructor or pretend disk-only state is proof of a
    // still-live Wintun generation; retain it until qualified v2 OS recovery.
    if journal.Schema==n4UnifiedSchemaNoWFP {
        return fmt.Errorf("%w: no-WFP v2 WAL requires live generation-owned four-stage recovery",ErrN4NativeGuard)
    }
    // Legacy v1 journal still requires its actual old WFP owner; migration
    // removes only exact-owned objects and never widens the cleanup scope.
    return N4WindowsRecoverPersistedPreRouteWAL(ctx,nativePath,journal.Identity)
}
