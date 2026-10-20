//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "os"
    "path/filepath"
    "strings"
)

// N4NativeStateSnapshot is an advisory, read-only report about disk state.
// It is NOT an OS ownership or WFP-readback certificate. No field here
// authorizes native Connect, routing, or recovery.
type N4NativeStateSnapshot struct {
    Schema string `json:"schema"`
    State string `json:"state"`
    LegacyJournal bool `json:"legacy_journal"`
    NativeWAL bool `json:"native_wal"`
    RouteIntent bool `json:"route_intent"`
    Phase string `json:"phase,omitempty"`
    RecordCount int `json:"record_count"`
    GuardQualified bool `json:"guard_qualified"`
}

const N4NativeStateSchema = "wbd-native-network-disk-status/v1"

// N4NativeInspectState never opens WFP, a TUN, the registry, or a shell.
// In particular, an intact SHA-checked journal is only a *disk* fact: it
// cannot prove a live Wintun owner or a fully installed persistent guard.
func N4NativeInspectState(ctx context.Context, statePath string)(N4NativeStateSnapshot,error){
    snap:=N4NativeStateSnapshot{Schema:N4NativeStateSchema, State:"unknown"}
    if ctx==nil{return snap,ErrNetworkPlan}
    if err:=ctx.Err();err!=nil{return snap,err}
    if strings.TrimSpace(statePath)=="" || !filepath.IsAbs(statePath){
        return snap,ErrNetworkPlan
    }
    wal:=statePath+".n4-owned-wal"
    paths:=[]string{statePath,wal,wal+".routes",statePath+".routes"}
    present:=[4]bool{}
    for i,path:=range paths{
        if err:=ctx.Err();err!=nil{return snap,err}
        info,err:=os.Lstat(path)
        if errors.Is(err,os.ErrNotExist){continue}
        if err!=nil{return snap,err}
        if info.Mode()&os.ModeSymlink!=0 || !info.Mode().IsRegular(){
            return snap,ErrN4JournalConflict
        }
        present[i]=true
    }
    snap.LegacyJournal=present[0]
    snap.NativeWAL=present[1]
    snap.RouteIntent=present[2]||present[3]
    if present[0]&&present[1]{
        snap.State="conflict"
        return snap,ErrN4JournalConflict
    }
    if present[1] {
        // Independently verify bounded WAL syntax and SHA before reporting.
        // This is never proof that the Windows host is in that WAL phase.
        journal,err:=n4UnifiedRead(wal)
        if err!=nil {
            snap.State="invalid_native_wal"
            return snap,errors.Join(ErrN4JournalConflict,err)
        }
        snap.Phase=journal.Phase
        snap.RecordCount=len(journal.Records)
        snap.State="native_wal_unverified"
    } else if snap.RouteIntent {
        snap.State="orphan_route_intent"
    } else if present[0] {
        snap.State="legacy_journal"
    } else {
        snap.State="absent"
    }
    return snap,ctx.Err()
}
