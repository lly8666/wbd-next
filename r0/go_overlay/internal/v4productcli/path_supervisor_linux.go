//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "context"
    "errors"
    "fmt"
    "log"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// A client path change is a COLD intent in the existing original-Go TLS
// admission lifecycle. All steady-state payload continues in the existing
// Rust M1/M3/M4 owners; the original shared TUN reader is not restarted.
// There is exactly ONE current owner, at most ONE pending new generation,
// and at most ONE old generation completing exact Rust Stop. A path notifier
// cannot drive an unbounded number of handshakes or native worker groups.
type originalClientGeneration struct{
    seq uint64
    path originalLinuxUnderlay
    cancel context.CancelFunc
    ready chan struct{}
    done chan error
}
func originalGenerationDone(a *originalClientGeneration)<-chan error{
    if a==nil{return nil}
    return a.done
}
func originalGenerationReady(a *originalClientGeneration)<-chan struct{}{
    if a==nil{return nil}
    return a.ready
}

// Synthetic session port is not a routing authority, but is new on every
// COLD connect, including an unchanged source IP with a new gateway.
// This is needed to have *both* A and B original FakeTCP associations alive.
func originalGenerationPort(base uint16,seq uint64)uint16{
    if seq==1{return base}
    candidate:=uint16(49152+(uint64(base)+seq*7919)%16383)
    if candidate==base{candidate++}
    return candidate
}
func startOriginalClientGeneration(
    parent context.Context,original config,tun *ownedTun,
    path originalLinuxUnderlay,seq uint64,overlap bool,
    previousPhysicalMTU int,
)(*originalClientGeneration,error){
    if !path.valid()||original.peerIP!=path.peer||original.sharedTun==nil{
        return nil,fmt.Errorf("native path candidate requires verified numeric physical endpoint and shared Rust TUN")
    }
    c:=original
    c.rawInterface=path.iface
    c.localIP=path.src
    c.localPort=originalGenerationPort(original.localPort,seq)
    c.leaseMustStay=overlap
    // New physical ceiling is read from the actual selected OS interface.
    // On overlap, do not increase an A-effective tunnel budget before A Stop:
    // keep B's cold offered record cap at least as conservative as old A.
    budgetMTU:=path.mtu
    if overlap&&previousPhysicalMTU>=576&&previousPhysicalMTU<budgetMTU{
        budgetMTU=previousPhysicalMTU
    }
    // Freeze the same bounded kernel path budget for the later protected
    // TLS authenticated callback; it must not use bare iface.MTU again.
    c.underlayBudgetMTU=budgetMTU
    cold,err:=realityfront.V4DeriveColdMTUBudget(realityfront.V4ColdMTUBudgetInput{
        ConfiguredOuterIPMTU:uint32(c.outerMTU),
        PhysicalOuterIPMTU:uint32(budgetMTU),
        IPv4HeaderBytes:20,TCPDataHeaderBytes:20,Mode:0,
    })
    if err!=nil{return nil,err}
    if cold.LocalSYNAdvertisedMSS<536||cold.LocalSYNAdvertisedMSS>1460{
        return nil,fmt.Errorf("new native physical path SYN MSS outside supported budget")
    }
    mss:=uint16(cold.LocalSYNAdvertisedMSS)
    if err=faketcp.SetPublicV4AdvertisedMSS(mss);err!=nil{return nil,err}
    c.recordLimit,c.innerMTU,err=deriveMTUBudget(c.outerMTU,budgetMTU,
        mss,0,c.fecMode,false,false)
    if err!=nil{return nil,err}
    raw,err:=faketcp.OpenRawIPv4EndpointWithOptions(
        c.rawInterface,c.localIP.As4(),faketcp.PacketPersonaLegacy,
        faketcp.RawIPv4EndpointOptions{ReceivePort:c.localPort},
    )
    if err!=nil{return nil,err}
    emit:=func(seg faketcp.Segment)error{
        _,e:=raw.WriteSegment(seg)
        return e
    }
    runCtx,cancel:=context.WithCancel(parent)
    a:=&originalClientGeneration{
        seq:seq,path:path,cancel:cancel,
        ready:make(chan struct{},1),done:make(chan error,1),
    }
    log.Printf("V4_PUBLIC_PATH_CANDIDATE role=client generation=%d ifindex=%d physical_mtu=%d outer_intent=%d mss=%d record_cap=%d source=kernel_route_get",
        seq,path.ifindex,path.mtu,c.outerMTU,cold.LocalSYNAdvertisedMSS,c.recordLimit)
    go func(){
        var connected bool
        err:=runClient(runCtx,c,path.ifindex,tun,raw,emit,seq>1,&connected,a.ready)
        err=errors.Join(err,raw.Close())
        a.done<-err
    }()
    return a,nil
}
func originalPathRetry(attempt int)time.Duration{
    if attempt<1{return time.Second}
    seconds:=1<<uint(min(attempt-1,4))
    if seconds>30{seconds=30}
    return time.Duration(seconds)*time.Second
}
func waitOriginalGenerationStop(a *originalClientGeneration)error{
    if a==nil{return nil}
    a.cancel()
    select{
    case err:=<-a.done:
        // Cancel is a legitimate local Stop; the Rust owner still must have
        // completed its native M4 join before runClient returns.
        if errors.Is(err,context.Canceled){return nil}
        return err
    case <-time.After(18*time.Second):
        return fmt.Errorf("original Rust generation %d Stop/driver join incomplete",a.seq)
    }
}

// Actual OS path-change client supervisor for numeric endpoints. No second
// Health90 controller: runClient still uses the original Rust terminal pulse;
// new generations are requested only by a changed kernel route/address or
// after the previous owner really terminates. Path events alone never mark
// a candidate ready or release an old authenticated owner.
func runOriginalLinuxClientPaths(
    ctx context.Context,c config,tun *ownedTun,
)(retErr error){
    initial,err:=readOriginalLinuxUnderlay(c.peerIP,c.tunName)
    if err!=nil{return err}
    events,err:=watchOriginalLinuxUnderlay(ctx,c.peerIP,c.tunName,initial)
    if err!=nil{return err}
    var current,candidate,retiring *originalClientGeneration
    desired:=initial
    var seq uint64
    var retry int
    var retryTimer *time.Timer
    var retryCh <-chan time.Time
    stopTimer:=func(){
        if retryTimer!=nil{
            if !retryTimer.Stop(){
                select{case <-retryTimer.C:default:}
            }
            retryTimer=nil
        }
        retryCh=nil
    }
    defer stopTimer()
    defer func(){
        // Candidate cannot be dropped while still owning original TLS
        // buffers, detached raw RX, or a Rust generation. Stop all before
        // Run's process-shared TUN reader Close and eventual kernel TUN FD.
        seen:=map[*originalClientGeneration]bool{}
        for _,a:=range []*originalClientGeneration{candidate,current,retiring}{
            if a!=nil&&!seen[a]{
                seen[a]=true
                a.cancel()
            }
        }
        for a:=range seen{
            retErr=errors.Join(retErr,waitOriginalGenerationStop(a))
        }
    }()
    scheduleRetry:=func(stage string){
        stopTimer()
        retry++
        delay:=originalPathRetry(retry)
        retryTimer=time.NewTimer(delay)
        retryCh=retryTimer.C
        log.Printf("V4_PUBLIC_PATH_RECONNECT_RETRY role=client reason=%s bounded_backoff_ms=%d current_owner_untouched=%t",
            stage,delay.Milliseconds(),current!=nil)
    }
    launch:=func()error{
        if candidate!=nil||retiring!=nil{return nil}
        if current!=nil&&desired==current.path{return nil}
        seq++
        previousMTU:=0
        if current!=nil{previousMTU=current.path.mtu}
        a,e:=startOriginalClientGeneration(ctx,c,tun,desired,seq,
            current!=nil,previousMTU)
        if e!=nil{return e}
        candidate=a
        return nil
    }
    if err=launch();err!=nil{return err}
    for {
        select{
        case <-ctx.Done():
            return nil
        case next,ok:=<-events:
            if !ok{
                if ctx.Err()!=nil{return nil}
                return fmt.Errorf("original Linux native route notifier closed")
            }
            if !next.valid()||next==desired{continue}
            desired=next
            retry=0
            stopTimer()
            if candidate!=nil{
                // A superseded candidate cannot commit READY after a newer
                // OS route snapshot. Keep A alive while it releases loans.
                candidate.cancel()
                continue
            }
            if retiring==nil{
                if err=launch();err!=nil{scheduleRetry("new_path_open")}
            }
        case <-originalGenerationReady(candidate):
            if candidate==nil{continue}
            a:=candidate
            if a.path!=desired||ctx.Err()!=nil{
                a.cancel()
                continue
            }
            // Check terminal return before promoting a possibly already
            // failed M4 generation. A live old owner remains untouched.
            select{
            case e:=<-a.done:
                log.Printf("V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=%d class=%s",
                    a.seq,nativeColdFailureClass(e))
                candidate=nil
                scheduleRetry("ready_then_terminal")
                continue
            default:
            }
            candidate=nil
            previous:=current
            current=a
            retry=0
            stopTimer()
            log.Printf("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=%d old_generation=%t source=real_original_TLS_Rust_M4 os_path_authority=1",
                a.seq,previous!=nil)
            if previous!=nil{
                retiring=previous
                previous.cancel()
            }
        case e:=<-originalGenerationDone(candidate):
            if candidate==nil{continue}
            superseded:=candidate.path!=desired
            log.Printf("V4_PUBLIC_PATH_CANDIDATE_FAILED role=client generation=%d class=%s old_untouched=%t superseded_by_new_OS_path=%t",
                candidate.seq,nativeColdFailureClass(e),current!=nil,superseded)
            candidate=nil
            if superseded{
                // A new effective physical path is new information; do not
                // impose an unrelated failed old candidate's 1-30s backoff.
                if retiring==nil{
                    if err=launch();err!=nil{scheduleRetry("superseding_path_open")}
                }
            }else{
                scheduleRetry("TLS_or_Rust_M4")
            }
        case e:=<-originalGenerationDone(current):
            if current==nil{continue}
            log.Printf("V4_PUBLIC_PATH_OLD_TERMINATED role=client generation=%d class=%s",
                current.seq,nativeColdFailureClass(e))
            current=nil
            if candidate==nil&&retiring==nil{scheduleRetry("Rust_dead_or_native_closed")}
        case e:=<-originalGenerationDone(retiring):
            if retiring==nil{continue}
            log.Printf("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=%d class=%s",
                retiring.seq,nativeColdFailureClass(e))
            retiring=nil
            if candidate==nil&&(current==nil||current.path!=desired){
                if err=launch();err!=nil{scheduleRetry("after_old_stop")}
            }
        case <-retryCh:
            stopTimer()
            if candidate==nil&&retiring==nil&&(current==nil||current.path!=desired){
                if err=launch();err!=nil{scheduleRetry("path_still_unavailable")}
            }
        }
    }
}
