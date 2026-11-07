//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "context"
    "errors"
    "fmt"
    "log"
    "math/rand"
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
type originalGameLaneTurn struct{
    done chan originalGameLaneTurnResult
}
type originalGameLaneTurnResult struct{
    lane uint8
    clientPort uint16
    err error
}
type originalClientGeneration struct{
    laneRotate chan originalGameLaneTurn
    seq uint64
    localPort uint16 // verified original FakeTCP tuple, diagnostic only
    path originalLinuxUnderlay
    cancel context.CancelFunc
    ready chan struct{}
    predead chan struct{} // rust-verified Health stale BEFORE terminal dead
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
func originalGenerationPreDead(a *originalClientGeneration)<-chan struct{}{
    if a==nil{return nil}
    return a.predead
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
// Game source ports form one immutable local 4-tuple set per cold group.
// All lanes retain server destination 443; reserve 4 consecutive client
// source ports and do not collide with an old-generation port.
func originalGenerationGamePort(base uint16,seq uint64,lanes uint8)(uint16,error){
 if lanes!=2&&lanes!=4{return 0,fmt.Errorf("invalid Game generation lane count")}
 port:=base
 if seq>1{
  port=uint16(49152+(uint64(base)+seq*7919)%16380)
  if port==base{port++}
 }
 if int(port)+int(lanes)-1>65535{
  return 0,fmt.Errorf("Game source ports overflow in cold generation")
 }
 return port,nil
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
    c.rotationGeneration=seq
    c.rawInterface=path.iface
    c.localIP=path.src
    c.localPort=originalGenerationPort(original.localPort,seq)
    if c.gameLanes!=0{
        port,e:=originalGenerationGamePort(original.localPort,seq,original.gameLanes)
        if e!=nil{return nil,e}
        c.localPort=port
    }
    // The same installation keeps its verified /32 across an overlapping
    // native Game cohort; Rust shared TUN publishes B only after M4 Ready.
    c.leaseMustStay=overlap||(c.gameLanes!=0&&seq>1)
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
        mss,0,c.fecMode,c.gameLanes!=0,c.gameFecEnabled)
    if err!=nil{return nil,err}
    if c.gameLanes!=0{
        // Reuse the original TLS/Rust Game group on the new native path.
        // ONE process Rust TUN reader selects the most recent authenticated
        // active Game group's default route. Existing A remains live until
        // B has authenticated, installed its MTU, and published its M4 owner.
        runCtx,cancel:=context.WithCancel(parent)
        a:=&originalClientGeneration{
            seq:seq,localPort:c.localPort,path:path,cancel:cancel,
            ready:make(chan struct{},1),done:make(chan error,1),
        }
        if c.gameLanes==4&&c.rotationInterval>0{
            a.laneRotate=make(chan originalGameLaneTurn)
        }
        log.Printf("V4_PUBLIC_PATH_CANDIDATE role=client generation=%d mode=game%d ifindex=%d physical_mtu=%d outer_intent=%d mss=%d record_cap=%d shared_tun_single_reader=1 old_owner_may_overlap=%t",
            seq,c.gameLanes,path.ifindex,path.mtu,c.outerMTU,cold.LocalSYNAdvertisedMSS,c.recordLimit,overlap)
        go func(){
            var connected bool
            a.done<-runGameClientGeneration(runCtx,c,path.ifindex,tun,&connected,a.ready,a.laneRotate)
        }()
        return a,nil
    }
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
        seq:seq,localPort:c.localPort,path:path,cancel:cancel,
        ready:make(chan struct{},1),predead:make(chan struct{},1),
        done:make(chan error,1),
    }
    log.Printf("V4_PUBLIC_PATH_CANDIDATE role=client generation=%d ifindex=%d physical_mtu=%d outer_intent=%d mss=%d record_cap=%d source=kernel_route_get",
        seq,path.ifindex,path.mtu,c.outerMTU,cold.LocalSYNAdvertisedMSS,c.recordLimit)
    go func(){
        var connected bool
        err:=runClient(runCtx,c,path.ifindex,tun,raw,emit,seq>1,&connected,a.ready,a.predead)
        err=errors.Join(err,raw.Close())
        a.done<-err
    }()
    return a,nil
}
// The jitter belongs to the ORIGINAL cold path supervisor only: it never
// alters Game copy staggering, FEC deadlines, retransmission or wire bytes.
func validateOriginalRotationInterval(role string, interval time.Duration)error{
    return validateOriginalRotationPolicy(role,interval,0)
}
func validateOriginalRotationPolicy(role string, interval,jitter time.Duration)error{
    if interval==0{
        if jitter!=0{return fmt.Errorf("rotation-jitter needs positive rotation-interval")}
        return nil
    }
    if role!="client"||interval<5*time.Second||interval>24*time.Hour{
        return fmt.Errorf("rotation-interval requires client and 5s..24h (0 disables)")
    }
    if jitter<0||jitter>interval/3||interval-jitter<5*time.Second{
        return fmt.Errorf("rotation-jitter requires 0..interval/3 and minimum actual interval 5s")
    }
    return nil
}
// An authenticated old generation can continue receiving while its verified
// successor is already sending. This is a bounded COLD retirement choice,
// never a TLS timeout or a reason to postpone explicit user Stop.
func originalLaneRetirementGrace()time.Duration{
    return 10*time.Second+time.Duration(rand.Int63n(int64(10*time.Second)+1))
}
func originalNextRotationDelay(interval,jitter time.Duration)time.Duration{
    if jitter==0{return interval}
    return interval-jitter+time.Duration(rand.Int63n(int64(2*jitter)+1))
}
func originalGenerationNeedsReplacement(current *originalClientGeneration,
    desired originalLinuxUnderlay,timerDue bool)bool{
    return current==nil||current.path!=desired||timerDue
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
// new generations are requested only by a changed kernel route/address,
// an explicit bounded rotation timer, or after the previous owner terminates. Path events alone never mark
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
    var rotationTimer *time.Timer
    var rotationCh <-chan time.Time
    var retireTimer *time.Timer
    var retireCh <-chan time.Time
    var timerDue bool
    var laneTurnCh <-chan originalGameLaneTurnResult
    var laneTurnOwner *originalClientGeneration
    var armedRotationDelay time.Duration
    stopRotation:=func(){
        if rotationTimer!=nil{
            if !rotationTimer.Stop(){select{case <-rotationTimer.C:default:}}
            rotationTimer=nil
        }
        rotationCh=nil
    }
    armRotation:=func(){
        stopRotation()
        if c.rotationInterval>0 && current!=nil && ctx.Err()==nil{
            armedRotationDelay=originalNextRotationDelay(c.rotationInterval,c.rotationJitter)
            rotationTimer=time.NewTimer(armedRotationDelay)
            rotationCh=rotationTimer.C
        }
    }
    defer stopRotation()
    stopRetireTimer:=func(){
        if retireTimer!=nil{
            if !retireTimer.Stop(){select{case <-retireTimer.C:default:}}
            retireTimer=nil
        }
        retireCh=nil
    }
    defer stopRetireTimer()
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
            stopErr:=waitOriginalGenerationStop(a)
            if a==retiring&&stopErr==nil{
                // Grace was interrupted by client Stop; the exact old
                // Rust join has completed, so this is a real retired owner.
                log.Printf("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=%d class=client-close grace_interrupted=1 native_joined=1",a.seq)
            }
            retErr=errors.Join(retErr,stopErr)
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
        if !originalGenerationNeedsReplacement(current,desired,timerDue){return nil}
        // Game and Normal now share one process-owned Rust TUN reader.
        // Do NOT retire healthy A yet: start the new original-TLS/M4
        // candidate, and retire A only in NEW_GENERATION_READY below.
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
            timerDue=false // a real path change supersedes the timed intent
            stopRotation()
            retry=0
            stopTimer()
            if candidate!=nil{
                // A superseded candidate cannot commit READY after a newer
                // OS route snapshot. Keep A alive while it releases loans.
                candidate.cancel()
                continue
            }
            if retiring!=nil{
                // An actual new NIC/IP supersedes the cosmetic grace. Never
                // stall the NEXT authenticated path behind a retired one.
                stopRetireTimer()
                retiring.cancel()
            }else if err=launch();err!=nil{scheduleRetry("new_path_open")}
        case <-originalGenerationPreDead(current):
            if current==nil||c.gameLanes!=0||ctx.Err()!=nil||
               candidate!=nil||retiring!=nil||timerDue{continue}
            // Still authenticated A is the live default route until B
            // independently finishes original TLS, M4 and AEAD Health.
            // A successful B retires A through the exact existing
            // randomized grace; a failed B leaves A unaffected.
            timerDue=true
            stopRotation()
            log.Printf("V4_PUBLIC_PATH_PREDEAD_AUTH_REFRESH role=client old_generation=%d authenticated_health_stale=1 old_route_preserved=1 terminal_native_dead=0",current.seq)
            if err=launch();err!=nil{scheduleRetry("preterminal_auth_refresh")}
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
            timerDue=false
            retry=0
            stopTimer()
            armRotation()
            log.Printf("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=%d old_generation=%t source=real_original_TLS_Rust_M4 os_path_authority=1 client_ipv4=%s client_port=%d",
                a.seq,previous!=nil,a.path.src.String(),a.localPort)
            if previous!=nil{
                if c.gameLanes!=0{
                    log.Printf("V4_PUBLIC_PATH_GAME_OVERLAP_COMMIT role=client new_generation=%d old_generation=%d shared_tun_single_reader=1 new_tls_m4_before_old_stop=1",
                        a.seq,previous.seq)
                }
                retiring=previous
                grace:=originalLaneRetirementGrace()
                retireTimer=time.NewTimer(grace)
                retireCh=retireTimer.C
                log.Printf("V4_PUBLIC_PATH_OLD_RETIRE_SCHEDULED role=client new_generation=%d old_generation=%d delay_ms=%d old_rx_alive=1 new_route_active=1",
                    a.seq,previous.seq,grace.Milliseconds())
            }
        case <-retireCh:
            stopRetireTimer()
            if retiring!=nil{
                log.Printf("V4_PUBLIC_PATH_OLD_GRACE_ELAPSED role=client generation=%d exact_stop_requested=1",retiring.seq)
                retiring.cancel()
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
            stopRotation()
            if candidate==nil&&retiring==nil{scheduleRetry("Rust_dead_or_native_closed")}
        case e:=<-originalGenerationDone(retiring):
            if retiring==nil{continue}
            stopRetireTimer()
            log.Printf("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=%d class=%s",
                retiring.seq,nativeColdFailureClass(e))
            retiring=nil
            if candidate==nil&&originalGenerationNeedsReplacement(current,desired,timerDue){
                if err=launch();err!=nil{scheduleRetry("after_old_stop")}
            }
        case answer:=<-laneTurnCh:
            laneTurnCh=nil
            owner:=laneTurnOwner
            laneTurnOwner=nil
            if owner!=current||current==nil||ctx.Err()!=nil{continue}
            if answer.err!=nil{
                if errors.Is(answer.err,errOriginalGameLaneColdCandidate){
                    log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_COLD_RETRY_ARMED role=client generation=%d class=%s current_owner_preserved=1",
                        current.seq,nativeColdFailureClass(answer.err))
                }else{
                    log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_FAILED role=client generation=%d class=%s",
                        current.seq,nativeColdFailureClass(answer.err))
                }
            }else{
                log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY role=client generation=%d lane=%d new_client_port=%d unaffected_sibling_lanes=3 original_TLS_Rust_M4=1",
                    current.seq,answer.lane,answer.clientPort)
            }
            armRotation()
        case <-rotationCh:
            stopRotation()
            if current==nil||ctx.Err()!=nil{continue}
            // A timer is allowed to replace the same healthy physical path;
            // unlike route notifications, it does NOT require NIC/IP change.
            // Fresh cold readback still applies any smaller current MTU.
            actual,e:=readOriginalLinuxUnderlay(c.peerIP,c.tunName)
            if e!=nil||!actual.valid(){
                log.Printf("V4_PUBLIC_TIMER_ROTATION_DEFER role=client reason=physical_path_unavailable")
                armRotation() // no spinning and no speculative network probe
                continue
            }
            // One protected lane at a time in the CURRENT Game4 group.
            // A true NIC/IP/MTU change still uses full-group original A+B.
            if c.gameLanes==4&&current.laneRotate!=nil&&
                actual==current.path&&candidate==nil&&retiring==nil{
                intent:=originalGameLaneTurn{
                    done:make(chan originalGameLaneTurnResult,1),
                }
                select{
                case current.laneRotate<-intent:
                    laneTurnCh=intent.done
                    laneTurnOwner=current
                    log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client generation=%d unchanged_path=1 actual_delay_ms=%d jitter_max_ms=%d",
                        current.seq,armedRotationDelay.Milliseconds(),
                        c.rotationJitter.Milliseconds())
                default:
                    log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_DEFER role=client reason=existing_original_group_busy")
                    armRotation()
                }
                continue
            }
            desired=actual
            timerDue=true
            log.Printf("V4_PUBLIC_TIMER_ROTATION_DUE role=client current_generation=%d same_physical_interface_ipv4=%t unchanged_path=%t interval_ms=%d actual_delay_ms=%d jitter_max_ms=%d unix_ms=%d",
                current.seq,current.path.samePhysicalInterfaceIPv4(actual),current.path==actual,
                c.rotationInterval.Milliseconds(),armedRotationDelay.Milliseconds(),c.rotationJitter.Milliseconds(),time.Now().UnixMilli())
            if candidate==nil&&retiring==nil{
                if err=launch();err!=nil{scheduleRetry("timer_cold_open")}
            }
        case <-retryCh:
            stopTimer()
            if candidate==nil&&retiring==nil&&originalGenerationNeedsReplacement(current,desired,timerDue){
                if err=launch();err!=nil{scheduleRetry("path_still_unavailable")}
            }
        }
    }
}
