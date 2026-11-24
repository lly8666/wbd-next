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
        // Route intents are not recoverable without their main WAL. Do
        // not clean a sibling Defender rule while route state is unresolved.
        for _,candidate:=range []string{nativePath+".routes",statePath+".routes"} {
            _,sideErr:=os.Lstat(candidate)
            if sideErr==nil{return fmt.Errorf("%w: orphan route sidecar without native WAL: %s",ErrN4JournalConflict,candidate)}
            if !errors.Is(sideErr,os.ErrNotExist){return sideErr}
        }
        // Only a standalone exact owned Defender receipt can be recovered:
        // checksum, generation-key, COM readback and CAS are all required.
        // Intent, foreign/modified, corrupt or inaccessible state stays OPEN.
        defender:=n4Plan029DefenderSidecarPath(statePath)
        if _,sideErr:=os.Lstat(defender);sideErr==nil {
            if e:=n4Plan029DefenderRecoverOrphan(ctx,defender,n4Plan029DefenderCOM{});e!=nil{
                return fmt.Errorf("%w: orphan Defender exact recovery failed: %w",ErrN4JournalConflict,e)
            }
        }else if !errors.Is(sideErr,os.ErrNotExist){return sideErr}
        return nil
    }
    if err!=nil{return err}
    if info.Mode()&os.ModeSymlink!=0 || !info.Mode().IsRegular(){
        return ErrN4JournalConflict
    }
    journal,err:=n4UnifiedRead(nativePath)
    if err!=nil{return err}
    if journal.Schema==n4UnifiedSchemaNoWFP {
        if err:=n4RecoverNoWFPPersisted(ctx,nativePath);err!=nil{return err}
        // The original per-generation Defender rule is separate from the
        // four stages. Use the existing exact orphan cleanup after routes.
        defender:=n4Plan029DefenderSidecarPath(statePath)
        if _,err:=os.Lstat(defender);err==nil {
            return n4Plan029DefenderRecoverOrphan(ctx,defender,n4Plan029DefenderCOM{})
        }else if !errors.Is(err,os.ErrNotExist){return err}
        return nil
    }
    // Legacy v1 journal still requires its actual old WFP owner; migration
    // removes only exact-owned objects and never widens the cleanup scope.
    return N4WindowsRecoverPersistedPreRouteWAL(ctx,nativePath,journal.Identity)
}
