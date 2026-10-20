//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "fmt"

    "github.com/tailscale/wf"
)

// n4ValidateExactWFPArmPlan validates an immutable, persistent native rule
// batch before opening an engine or mutating any host state. It is NOT an
// admission/ownership decision; the product Arm remains fail-closed until
// Wintun, WAL, authenticated Stop and isolated network qualification exist.
func n4ValidateExactWFPArmPlan(p n4WFPRulePlan) error {
    if p.Sublayer==nil || p.Sublayer.ID==(wf.SublayerID{}) ||
        !p.Sublayer.Persistent || len(p.Rules)==0 || len(p.Rules)>8 {
        return ErrN4NativeGuard
    }
    seen:=make(map[wf.RuleID]bool,len(p.Rules))
    for _,r:=range p.Rules {
        if r==nil || r.ID==(wf.RuleID{}) || seen[r.ID] ||
            r.Sublayer!=p.Sublayer.ID || !r.Persistent || r.BootTime ||
            r.Disabled || r.Action!=wf.ActionBlock || len(r.Conditions)==0 {
            return ErrN4NativeGuard
        }
        seen[r.ID]=true
    }
    return nil
}

// n4WFPArmExactPlan is a package-private native OS primitive, never a
// product entry or CLI switch. Tests may exercise only narrowly scoped
// TEST-NET plans on an explicitly isolated and recoverable host. Calling
// this helper alone does NOT qualify production global IPv6/DNS filters.
//
// The owner must have durably persisted the guard intent BEFORE invocation.
// If any host write fails, remove only objects installed by this invocation.
// A failed rollback remains an explicit error; the higher-level WAL must be
// preserved. A new independent WFP engine checks the final installed batch.
func n4WFPArmExactPlan(ctx context.Context,p n4WFPRulePlan) error {
    if ctx==nil{return ErrNetworkPlan}
    if err:=ctx.Err();err!=nil{return err}
    if err:=n4ValidateExactWFPArmPlan(p);err!=nil{return err}
    session,err:=wf.New(&wf.Options{Dynamic:false})
    if err!=nil{return err}
    // Exact preflight refuses collisions/foreign objects BEFORE writes.
    present,matching,err:=n4WFPReadOwned(session,p)
    if err!=nil {return errors.Join(err,session.Close())}
    if present || len(matching)!=0 {
        return errors.Join(ErrN4JournalConflict,session.Close())
    }
    if err:=ctx.Err();err!=nil{return errors.Join(err,session.Close())}
    if err:=session.AddSublayer(p.Sublayer);err!=nil{
        return errors.Join(err,session.Close())
    }
    added:=make([]wf.RuleID,0,len(p.Rules))
    var applyErr error
    for _,rule:=range p.Rules {
        if err:=ctx.Err();err!=nil{applyErr=err;break}
        if err:=session.AddRule(rule);err!=nil{
            applyErr=fmt.Errorf("native WFP add exact-owned rule: %w",err)
            break
        }
        added=append(added,rule.ID)
    }
    if applyErr!=nil {
        var rollbackErr error
        for i:=len(added)-1;i>=0;i--{
            rollbackErr=errors.Join(rollbackErr,session.DeleteRule(added[i]))
        }
        rollbackErr=errors.Join(rollbackErr,session.DeleteSublayer(p.Sublayer.ID))
        rollbackErr=errors.Join(rollbackErr,session.Close())
        // Do not report a successful rollback based solely on API return.
        check,e:=wf.New(&wf.Options{Dynamic:false})
        if e!=nil{return errors.Join(applyErr,rollbackErr,e)}
        sub,remaining,e:=n4WFPReadOwned(check,p)
        closeErr:=check.Close()
        if e!=nil || sub || len(remaining)!=0 {
            rollbackErr=errors.Join(rollbackErr,ErrN4NativeGuard)
        }
        return errors.Join(applyErr,rollbackErr,e,closeErr)
    }
    if err:=session.Close();err!=nil{return err}
    if err:=ctx.Err();err!=nil{return err}
    // The WFP handles are not authority: rules must survive engine close.
    check,err:=wf.New(&wf.Options{Dynamic:false})
    if err!=nil{return err}
    sub,matching,err:=n4WFPReadOwned(check,p)
    closeErr:=check.Close()
    if err!=nil{return errors.Join(err,closeErr)}
    if closeErr!=nil{return closeErr}
    if !sub || len(matching)!=len(p.Rules) {
        return ErrN4NativeGuard
    }
    for _,rule:=range p.Rules{
        if !matching[rule.ID]{return ErrN4NativeGuard}
    }
    return nil
}
