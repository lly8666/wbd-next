//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

// The genuine original-Go Game2/4 Linux process: 2/4 independent original
// FakeTCP/TLS sockets, one Rust GameAdapter and true M4 raw/TUN workers.
// No V3 transport, no standalone generated key and no fake Connected bit.
import (
    "context"
    "crypto/tls"
    "errors"
    "fmt"
    "log"
    "sync"
    "sync/atomic"
    "time"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)
// Only pre-Rust-M4 original Go TLS/association failures may be retried.
var errOriginalGameLaneColdCandidate=errors.New("new Game4 cold TLS candidate not installed")

func gamePort(base uint16,lane int)(uint16,error){
    value:=int(base)+lane
    if value<1||value>65535{return 0,fmt.Errorf("Game 2/4 per-lane FakeTCP port overflow")}
    return uint16(value),nil
}
func runGame(ctx context.Context,c config,ifindex uint32,tun *ownedTun,leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,connected *bool)error{
    // A shared listener has no process-global Game lane count: each
    // authenticated TLS request supplies its existing protected 1/2/4
    // policy, then runGameMultiServer groups Game cohorts independently.
    // Normal client/server paths and existing standalone Game2/4 stay exact.
    if c.mixedModes{
        if c.role!="server"||c.gameLanes!=0||
            (!c.leasePool.IsValid()&&len(c.manualClientLeases4)==0){
            return realityfront.ErrAdmissionUnsupported
        }
    }else if c.gameLanes!=2&&c.gameLanes!=4{
        return realityfront.ErrAdmissionUnsupported
    }
    if c.role=="client"{return runGameClient(ctx,c,ifindex,tun,connected,nil)}
    return runGameServer(ctx,c,ifindex,tun,leases,epochs,connected)
}

func repeatOriginalDetachedTLSFinalACK(ctx context.Context,assocs ...*faketcp.ClientAssociation){
    // The genuine FakeTCP server Write blocks on the final TLS reply
    // cumulative ACK. After M4 handoff the old Go filter intentionally
    // never receives retransmitted TLS DATA. Duplicate only the frozen
    // already-verified ACK, on the original tuple, for <=4.5 seconds.
    // This is a finite cold-commit guard, not a new DATA/repair controller.
    go func(){
        previous:=time.Duration(0)
        emitted:=0
        for _,delay:=range [...]time.Duration{
            80*time.Millisecond,240*time.Millisecond,560*time.Millisecond,
            1120*time.Millisecond,2240*time.Millisecond,4480*time.Millisecond,
        }{
            timer:=time.NewTimer(delay-previous)
            select{
            case <-ctx.Done():
                timer.Stop()
                return
            case <-timer.C:
            }
            previous=delay
            for _,a:=range assocs{
                if a==nil||a.State()!=faketcp.ClientAssociationDetached{continue}
                if err:=a.RepeatDetachedBootstrapACK();err==nil{emitted++}
            }
        }
        log.Printf("V4_PUBLIC_TLS_REPLY_ACK_COLD_GUARD role=client lanes=%d duplicate_pure_acks=%d window_ms=4480 new_wire_fields=0",
            len(assocs),emitted)
    }()
}

// Planned is the original bounded FEC owner count; sent requires at
// least ONE definite kernel M4 copy per Game logical parity row. Recovery
// count here is authenticated decoder candidate, not claimed TUN delivery.
func logOriginalGameFec(role string,n int,p *realityfront.V4LinuxGameProduct){
    proof,err:=p.FecCounters()
    if err!=nil{
        log.Printf("V4_PUBLIC_GAME_FEC_COUNTERS_NOT_AVAILABLE role=%s error=%v",role,err)
        return
    }
    log.Printf("V4_PUBLIC_GAME_FEC_COUNTERS role=%s lanes=%d source_offered=%d parity_offered=%d parity_copied=%d systematic_candidate=%d recovered_candidate=%d expired=%d failed=%d rplanned=%d rsent=%d retained_bytes=%d fec_rx_invalid=%d fec_rx_conflict=%d fec_rx_capacity=%d fec_rx_codec=%d fec_rx_state=%d fec_rx_frame=%d",
        role,n,proof.SourceOffered,proof.ParityOffered,
        proof.ParityKernelCopied,proof.SourceCandidate,proof.RecoveredCandidate,
        proof.Expired,proof.Failed,proof.Planned,proof.Sent,proof.RetainedBytes,
        proof.RxInvalid,proof.RxConflict,proof.RxCapacity,
        proof.RxCodec,proof.RxState,proof.RxFrame)
}
func logGameOuterRepair(role string,n int,p *realityfront.V4LinuxGameProduct,off bool)error{
    proof,err:=p.OuterPolicy()
    if err!=nil{return err}
    if proof.RepairEnabled==off{return realityfront.ErrAdmissionUnsupported}
    if off&&proof.DataRetransmitted!=0{return realityfront.ErrAdmissionUnsupported}
    log.Printf("V4_PUBLIC_GAME_OUTER role=%s lanes=%d repair_enabled=%d outer_data_retransmitted=%d blocked_duplicate=%d first_lane_copied=%d parity_separate=1",
        role,n,func()int{if proof.RepairEnabled{return 1};return 0}(),
        proof.DataRetransmitted,proof.BlockedDuplicate,proof.FirstLaneCopied)
    return nil
}
func logGame4CopySchedule(role string,p *realityfront.V4LinuxGameProduct,enabled,wide bool)error{
    row,err:=p.CopyScheduleRead()
    if err!=nil{return err}
    want:=uint64(0)
    if enabled{want=1}
    if wide{want=2}
    if row[0]!=want{return realityfront.ErrAdmissionUnsupported}
    log.Printf("V4_PUBLIC_GAME4_COPY_SCHEDULE role=%s mode=%d planned=%d,%d,%d,%d sent=%d,%d,%d,%d abandoned=%d,%d,%d,%d late_max_us=%d,%d,%d,%d late_mean_us=%d,%d,%d,%d",
        role,row[0],row[1],row[2],row[3],row[4],
        row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],
        row[13],row[14],row[15],row[16],row[17],row[18],row[19],row[20])
    return nil
}
// The shared PLAN028 physical path supervisor alone owns fresh Game cold
// generations. Its ready receipt is published ONLY after real Go TLS, Rust
// M4 activation and exact raw kernel handoff; never on SYN or Go parser state.
func runGameClientGeneration(
 ctx context.Context,c config,ifindex uint32,tun *ownedTun,
 connected *bool,ready chan<- struct{},
 rotation <-chan originalGameLaneTurn,
)error{
 return runGameClient(ctx,c,ifindex,tun,connected,ready,rotation)
}
func runGameClient(
 ctx context.Context,c config,ifindex uint32,tun *ownedTun,
 connected *bool,ready chan<- struct{},
 rotations ...<-chan originalGameLaneTurn,
)error{
    var rotation <-chan originalGameLaneTurn
    if len(rotations)>0{rotation=rotations[0]}
    n:=int(c.gameLanes)
    // Same original protected 10-byte V3 policy as Normal; each Game
    // client's authenticated cipher is independent of other cohorts.
    policy,err:=realityfront.PolicyForClientWithInitialAndCipher(
        int(c.gameLanes),"fixed",4,4,20,c.recordCipher)
    if err!=nil{return err}
    raws:=make([]*faketcp.RawIPv4Endpoint,0,n)
    assocs:=make([]*faketcp.ClientAssociation,0,n)
    // One original client cold RTO driver per independently authenticated
    // TLS/FakeTCP lane. All stop before M4 DATA or candidate teardown.
    coldRTOStops:=make([]func()(uint64,error),0,n)
    defer func(){for _,stop:=range coldRTOStops{_,_=stop()}}()
    flows:=make([]faketcp.ClientFlow,0,n)
    var handoffCommitted atomic.Bool
    var goPostHandoffDataCopies atomic.Uint64
    defer func(){
        for _,raw:=range raws{raw.Close()}
        for _,a:=range assocs{a.Close()}
    }()
    // The old FakeTCP tuple may still receive delayed cold records after
    // Rust has atomically swapped ONE hot Game4 slot. Retain that old cold
    // observer briefly; it never transmits DATA or becomes a second M4 lane.
    lingerCtx,lingerCancel:=context.WithCancel(ctx)
    var lingerWG sync.WaitGroup
    defer func(){lingerCancel();lingerWG.Wait()}()
    fail:=make(chan error,n)
    retiredRX:=make([]chan struct{},0,n)
    startRX:=func(a *faketcp.ClientAssociation,r *faketcp.RawIPv4Endpoint,
        f faketcp.ClientFlow,retired <-chan struct{}){
        go func(){
            for{
                seg,_,readErr:=r.ReadSegment()
                if readErr!=nil{
                    select{
                    case <-ctx.Done():return
                    case <-retired:return
                    default:
                    }
                    select{case fail<-readErr:default:}
                    return
                }
                if !f.MatchesInbound(seg){continue}
                if a.State()!=faketcp.ClientAssociationDetached{
                    if err:=a.HandleSegment(seg,time.Now());err!=nil&&
                        !errors.Is(err,faketcp.ErrClientDetached){
                        select{case fail<-err:default:}
                    }
                }else if len(seg.Payload)!=0&&handoffCommitted.Load(){
                    goPostHandoffDataCopies.Add(1)
                }
            }
        }()
    }
    for i:=0;i<n;i++{
        local,err:=gamePort(c.localPort,i)
        if err!=nil{return err}
        // Multiple independent client source ports still use ONE real
        // server destination port. Rust authenticates each exact 5-tuple.
        remote:=c.peerPort
        raw,e:=faketcp.OpenRawIPv4EndpointWithOptions(
            c.rawInterface,c.localIP.As4(),faketcp.PacketPersonaLegacy,
            faketcp.RawIPv4EndpointOptions{ReceivePort:local},
        )
        if e!=nil{return e}
        raws=append(raws,raw)
        emit:=func(seg faketcp.Segment)error{_,e:=raw.WriteSegment(seg);return e}
        flow:=faketcp.ClientFlow{LocalIP:c.localIP.As4(),PeerIP:c.peerIP.As4(),
            LocalPort:local,PeerPort:remote}
        flows=append(flows,flow)
        isn,e:=originalRandomISN()
        if e!=nil{return e}
        assoc,e:=faketcp.NewClientAssociation(flow,isn,time.Second,emit)
        if e!=nil{return e}
        assocs=append(assocs,assoc)
        retiredRX=append(retiredRX,make(chan struct{}))
        startRX(assoc,raw,flow,retiredRX[i])
        if e=assoc.Start(time.Now());e!=nil{return e}
        establish,cancel:=context.WithTimeout(ctx,20*time.Second)
        e=waitForOriginalColdSYN(establish,assoc)
        cancel()
        if e!=nil{return e}
        coldRTOStops=append(coldRTOStops,driveOriginalClientColdBootstrapRTO(ctx,assoc))
    }
    log.Printf("V4_PUBLIC_GAME_SINGLE_SERVER_PORT role=client lanes=%d server_port=%d distinct_local_ports=%d",
        n,c.peerPort,len(flows))
    // The original one process TUN and shared Rust kernel reader survive
    // simultaneous A+B native Game groups. Old A Close() must not close
    // the TUN/reader after B has published its newer default route.
    // The top-level CLI owns final Close after all groups drain.
    cleanup:=func()error{return tun.Close()}
    if c.autoIP{cleanup=func()error{return nil}}
    applyLease:=configureAuthenticatedClientIPv4(tun)
    if c.leaseMustStay{
        applyLease=func(lease string)error{
            if lease!=tun.cidr{
                return fmt.Errorf("new authenticated Game generation changed the same installation /32")
            }
            return configureAuthenticatedClientIPv4(tun)(lease)
        }
    }
    native,err:=realityfront.NewV4LinuxGameClientProduct(
        realityfront.V4LinuxGameProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,SharedTun:c.sharedTun,
            CleanupOwnedNetwork:cleanup,
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            ConfigureLeaseIPv4:applyLease,
            GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
            DisableOuterRepair:c.disableOuterRepair,
            Game4CopyStagger:c.game4CopyStagger,
            Game4CopyWideStagger:c.game4CopyWideStagger,
        })
    if err!=nil{return err}
    cfg:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{
            ServerName:c.serverName,RouteKey:c.routeKey,VerifyServer:true,RootCAs:c.tlsRoots,Timeout:15*time.Second,
        },
        Username:c.username,Password:c.password,TunnelID:c.tunnel[:],
        AutoLease:c.autoIP,InstallationID:c.installation[:],
        ClientLimit:c.recordLimit,DesiredLanes:c.gameLanes,Policy:policy,
    }
    dialCtx,cancel:=context.WithTimeout(ctx,60*time.Second)
    err=native.ConnectClientGame(dialCtx,assocs,cfg)
    cancel()
    for _,stop:=range coldRTOStops{
        actual,rtoErr:=stop()
        if actual>0{
            log.Printf("V4_PUBLIC_FAKETCP_CLIENT_COLD_DATA_RTO role=client mode=game lanes=%d actual_original_retransmissions=%d post_detach=0",
                n,actual)
        }
        err=errors.Join(err,rtoErr)
    }
    if err!=nil{_ = native.Close();return err}
    // Never filter Go TLS/bootstrap before the authenticated Rust receiver
    // and ownership transfer have both completed.
    for i,r:=range raws{
        if assocs[i].State()!=faketcp.ClientAssociationDetached{
            _=native.Close()
            return fmt.Errorf("Game client lane %d not detached at M4 handoff",i+1)
        }
        if e:=r.ExcludeDetachedData(flows[i].PeerIP,flows[i].PeerPort);e!=nil{
            _=native.Close()
            return fmt.Errorf("Game client lane %d kernel RX handoff: %w",i+1,e)
        }
    }
    handoffCommitted.Store(true)
    repeatOriginalDetachedTLSFinalACK(ctx,assocs...)
    if c.rotationGeneration>1&&c.sharedTun!=nil{
        // This new authenticated Game2/4 group may be READY locally while
        // the remote 443 server has only committed ONE of its independent
        // TLS lanes. Rust defers replacing A's shared TUN default route.
        // Require genuine B Game M4 AEAD/replay + TUN delivery, OR the
        // server's canonical encrypted native Health kind0 sent only after
        // its entire B Game M4 group committed. No business or reverse
        // user payload is needed for a no-traffic or pure-uplink switch.
        err=waitOriginalNativeM4PeerProof(ctx,
            func()(realityfront.V4PublicLoopPulse,error){
                proof,e:=native.KernelCounters()
                if e!=nil{return realityfront.V4PublicLoopPulse{},e}
                return realityfront.V4PublicLoopPulse{
                    RxRecords:proof.Delivered,
                    AuthenticatedPeerControl:proof.AuthenticatedPeerControl,
                },nil
            },
            native.PromoteGameAfterAuthenticatedPeerRx,5*time.Second)
        if err!=nil{
            log.Printf("V4_PUBLIC_GAME_REMOTE_M4_UNPROVEN role=client generation=%d lanes=%d old_tun_route_preserved=1",
                c.rotationGeneration,n)
            return errors.Join(err,native.Close())
        }
        log.Printf("V4_PUBLIC_GAME_REMOTE_M4_PROVEN role=client generation=%d lanes=%d native_authenticated_control_or_ipv4=1 tun_route_promoted=1",
            c.rotationGeneration,n)
    }
    // Each original TLS/FakeTCP association has its own kernel tuple and
    // has passed protected cold validation before the single grouped Rust
    // GameAdapter commits M4. Do not mislabel this as an independent hot
    // lane replacement; all four lanes commit as ONE group today.
    for i,flow:=range flows{
        log.Printf("V4_PUBLIC_GAME_GROUP_LANE_READY role=client group_generation=%d lane=%d local_port=%d server_port=%d protected_TLS=1 original_Rust_M4=1 grouped_commit=1",
            c.rotationGeneration,i+1,flow.LocalPort,flow.PeerPort)
    }
    log.Printf("V4_PUBLIC_GAME_GO_RX_HANDOFF role=client lanes=%d filtered=%d rust_ready=1 original_send_fd_open=1",n,n)
    *connected=true
    log.Printf("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=%d original_tls=1 rust_m4=1",n)
    if ready!=nil{select{case ready<-struct{}{}:default:}}
    if c.gameFecEnabled{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=%d mode=fixed profile=%d auth_original_tls=1 original_M4=1",n,c.gameFecProfile)
    }else{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=%d mode=off profile=0 auth_original_tls=1 original_M4=1",n)
    }
    // This product retains ONE native M4 GameAdapter. The sole existing
    // path supervisor delivers timer intents here; every successful intent
    // creates exactly ONE new original TLS association in the SAME epoch,
    // swaps only its Rust physical slot and stops only its old FakeTCP owner.
    // A cold TLS candidate can fail on an impaired carrier without touching
    // the old owner. Keep all four native M4 lanes alive and retry at the
    // ORIGINAL supervisor's next randomized timer; no second controller.
    laneRound:=uint64(1)
    nextLane:=0
    rotateOne:=func()(uint8,uint16,error){
        if n!=4{return 0,0,realityfront.ErrAdmissionUnsupported}
        slot:=nextLane
        lane:=uint8(slot+1)
        laneRound++
        first,e:=originalGenerationGamePort(c.localPort,laneRound,4)
        if e!=nil{return lane,0,e}
        local,e:=gamePort(first,slot)
        if e!=nil{return lane,0,e}
        oldFlow:=flows[slot]
        if local==oldFlow.LocalPort{return lane,0,fmt.Errorf("Game4 hot lane source port reused")}
        newRaw,e:=faketcp.OpenRawIPv4EndpointWithOptions(
            c.rawInterface,c.localIP.As4(),faketcp.PacketPersonaLegacy,
            faketcp.RawIPv4EndpointOptions{ReceivePort:local},
        )
        if e!=nil{return lane,0,errors.Join(errOriginalGameLaneColdCandidate,e)}
        var committed bool
        var newAssoc *faketcp.ClientAssociation
        freshRetired:=make(chan struct{})
        defer func(){
            if !committed{
                close(freshRetired)
                if newAssoc!=nil{newAssoc.Close()}
                newRaw.Close()
            }
        }()
        nextFlow:=faketcp.ClientFlow{
            LocalIP:c.localIP.As4(),PeerIP:c.peerIP.As4(),
            LocalPort:local,PeerPort:c.peerPort,
        }
        isn,e:=originalRandomISN()
        if e!=nil{return lane,0,e}
        emit:=func(seg faketcp.Segment)error{
            _,e:=newRaw.WriteSegment(seg)
            return e
        }
        newAssoc,e=faketcp.NewClientAssociation(nextFlow,isn,time.Second,emit)
        if e!=nil{return lane,0,errors.Join(errOriginalGameLaneColdCandidate,e)}
        startRX(newAssoc,newRaw,nextFlow,freshRetired)
        if e=newAssoc.Start(time.Now());e!=nil{
            return lane,0,errors.Join(errOriginalGameLaneColdCandidate,e)
        }
        establish,cancel:=context.WithTimeout(ctx,20*time.Second)
        e=waitForOriginalColdSYN(establish,newAssoc)
        cancel()
        if e!=nil{return lane,0,errors.Join(errOriginalGameLaneColdCandidate,e)}
        // The original server authenticates each cold TLS lane with a
        // 15s cap. A failed 5%-loss candidate must not hold its healthy
        // Game4 owner for a pointless 60s before trying another port.
        dialCtx,dialCancel:=context.WithTimeout(ctx,20*time.Second)
        stopColdRTO:=driveOriginalClientColdBootstrapRTO(dialCtx,newAssoc)
        e=native.ReplaceClientGameLane(dialCtx,newAssoc,cfg,lane)
        actual,rtoErr:=stopColdRTO()
        dialCancel()
        if actual>0{
            log.Printf("V4_PUBLIC_FAKETCP_CLIENT_COLD_DATA_RTO role=client mode=game4_hot lane=%d actual_original_retransmissions=%d post_detach=0",
                lane,actual)
        }
        e=errors.Join(e,rtoErr)
        if e!=nil{
            if errors.Is(e,realityfront.ErrV4GameLaneUncommittedCold){
                return lane,0,errors.Join(errOriginalGameLaneColdCandidate,e)
            }
            return lane,0,e
        }
        // Real Rust M4 has acknowledged selected slot handover. A fresh
        // Go-only raw observer may no longer claim native application DATA.
        if newAssoc.State()!=faketcp.ClientAssociationDetached{
            return lane,0,fmt.Errorf("new Game4 lane not detached after real M4 hot replace")
        }
        if e=newRaw.ExcludeDetachedData(nextFlow.PeerIP,nextFlow.PeerPort);e!=nil{
            return lane,0,e
        }
        oldRaw:=raws[slot]
        oldAssoc:=assocs[slot]
        oldRetired:=retiredRX[slot]
        raws[slot]=newRaw
        assocs[slot]=newAssoc
        flows[slot]=nextFlow
        retiredRX[slot]=freshRetired
        committed=true
        repeatOriginalDetachedTLSFinalACK(ctx,newAssoc)
        grace:=originalLaneRetirementGrace()
        lingerWG.Add(1)
        go func(){
            defer lingerWG.Done()
            timer:=time.NewTimer(grace)
            defer timer.Stop()
            select{case <-lingerCtx.Done():case <-timer.C:}
            close(oldRetired)
            oldRaw.Close()
            oldAssoc.Close()
        }()
        log.Printf("V4_PUBLIC_GAME_OLD_COLD_TUPLE_RETIRE_SCHEDULED role=client lane=%d old_port=%d delay_ms=%d same_M4_slot=1",
            lane,oldFlow.LocalPort,grace.Milliseconds())
        for sibling,flow:=range flows{
            if sibling==slot{continue}
            if flow.LocalPort==local{
                return lane,0,fmt.Errorf("hot one-lane port collides with untouched sibling %d",sibling+1)
            }
        }
        nextLane=(nextLane+1)%4
        log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=%d lane=%d cycle=%d old_client_port=%d new_client_port=%d unchanged_siblings=3 original_TLS_Rust_M4=1",
            c.rotationGeneration,lane,laneRound-1,oldFlow.LocalPort,local)
        return lane,local,nil
    }
    draining:=false
    for !draining{
        select{
        case <-ctx.Done():draining=true
        case err=<-fail:draining=true
        case turn,ok:=<-rotation:
            if !ok{rotation=nil;continue}
            lane,local,rotateErr:=rotateOne()
            turn.done<-originalGameLaneTurnResult{
                lane:lane,clientPort:local,err:rotateErr,
            }
            if errors.Is(rotateErr,errOriginalGameLaneColdCandidate){
                log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client lane=%d generation=%d owner_preserved=1 class=%s",
                    lane,c.rotationGeneration,nativeColdFailureClass(rotateErr))
                continue
            }
            if rotateErr!=nil{
                // An uncertain half-transition is never silently retried:
                // join the whole group and let the original one supervisor
                // perform a fresh cold generation if necessary.
                err=rotateErr
                draining=true
            }
        }
    }
    log.Printf("V4_PUBLIC_GAME_GO_RX_POST_HANDOFF role=client lanes=%d go_data_full_copies=%d",n,goPostHandoffDataCopies.Load())
    counters,countErr:=native.KernelCounters()
    if countErr==nil{
        log.Printf("V4_PUBLIC_GAME_KERNEL role=client lanes=%d copied=%d delivered=%d rejected=%d raw_received=%d auth_rejected=%d",
            n,counters.Copied,counters.Delivered,counters.Rejected,
            counters.RawReceived,counters.AuthenticatedRejected)
    }
    if errOuter:=logGameOuterRepair("client",n,native,c.disableOuterRepair);errOuter!=nil{
        err=errors.Join(err,errOuter)
    }
    if c.gameFecEnabled{logOriginalGameFec("client",n,native)}
    if n==4{
        if e:=logGame4CopySchedule("client",native,c.game4CopyStagger,c.game4CopyWideStagger);e!=nil{
            err=errors.Join(err,e)
        }
    }
    // Even a failed cold readback must not skip exact M4 native Stop.
    closeErr:=native.Close()
    if closeErr==nil{log.Printf("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=%d",n)}
    return errors.Join(err,closeErr)
}
func runGameServer(ctx context.Context,c config,ifindex uint32,tun *ownedTun,leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,connected *bool)(retErr error){
    n:=int(c.gameLanes)
    cert,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    if epochs==nil{return realityfront.ErrAdmissionParams}
    // Server auto-lease is enabled by --lease-pool, NEVER --auto-ip
    // (the latter is client-only). H1036's c.autoIP check could never be
    // reached on a valid server; use actual verified lease-pool authority.
    if c.leasePool.IsValid()||c.manualClientLease4.IsValid()||
       len(c.manualClientLeases4)>0{
        // Reuse original protected Game multi-generation 443 listener.
        return runGameMultiServer(ctx,c,ifindex,tun,leases,epochs,connected,cert)
    }
    // Manual old one-group mode remains exactly the original dedicated
    // physical TUN owner until the multi-group server path is qualified.
    native,err:=realityfront.NewV4LinuxGameServerProduct(
        realityfront.V4LinuxGameProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,
            CleanupOwnedNetwork:tun.Close,
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
            DisableOuterRepair:c.disableOuterRepair,
            Game4CopyStagger:c.game4CopyStagger,
            Game4CopyWideStagger:c.game4CopyWideStagger,
            Epochs:epochs,PeerPersona:c.peerPersona,Authenticate:originalV4CredentialCheck(c),
        })
    if err!=nil{return err}
    // One real AF_PACKET listener per server port, not one port or Go
    // socket per Game lane. Cold FakeTCP connection key is the immutable
    // client/server IPv4+port tuple. Only Rust can consume detached DATA.
    rawPersona:=faketcp.PacketPersonaLegacy
    if c.peerPersona==realityfront.V4PeerWindows11{
        rawPersona=faketcp.PacketPersonaWindows11
    }
    raw,err:=faketcp.OpenRawIPv4EndpointWithOptions(
        c.rawInterface,c.localIP.As4(),rawPersona,
        faketcp.RawIPv4EndpointOptions{ReceivePort:c.localPort},
    )
    if err!=nil{return err}
    defer raw.Close()
    emit:=func(seg faketcp.Segment)error{_,e:=raw.WriteSegment(seg);return e}
    table,err:=faketcp.NewServerAssociationTable(32,emit)
    if err!=nil{return err}
    assocs:=make([]*faketcp.ServerAssociation,n)
    var handoffCommitted atomic.Bool
    var goPostHandoffDataCopies atomic.Uint64
    admitted:=make(chan *faketcp.ServerAssociation,n)
    failed:=make(chan error,n)
    go func(){
        // This is COLD bootstrap only. All four established raw flows are
        // collected before protected TLS policies bind their lane IDs; the
        // native Game adapter still owns exactly one TUN reader for the group.
        seen:=make(map[faketcp.ServerFlow]bool,n)
        for{
            seg,_,readErr:=raw.ReadSegment()
            if readErr!=nil{
                select{case <-ctx.Done():return;default:}
                select{case failed<-readErr:default:}
                return
            }
            if seg.DstPort!=c.localPort{continue}
            if faketcp.IsInitialSYN(seg){
                // Leave existing retransmitted SYN/ACK behavior intact;
                // do not admit a fifth independently originated flow.
                if table.Len()>=n{
                    if _,ok:=table.GetSegment(seg);!ok{continue}
                }
                isn,e:=originalRandomISN()
                if e!=nil{select{case failed<-e:default:};return}
                a,e:=table.AddSYN(seg,isn,time.Second)
                if errors.Is(e,faketcp.ErrAssociationExists){continue}
                if e!=nil{select{case failed<-e:default:};return}
                synack,e:=a.SYNACKSegment()
                if e==nil{e=emit(synack)}
                if e!=nil{select{case failed<-e:default:};return}
                continue
            }
            a,ok:=table.GetSegment(seg)
            if !ok||a.State()==faketcp.ServerAssociationClosed{continue}
            if state,exists:=a.TransitionState();exists&&
               state==faketcp.TransitionDetached{
                if len(seg.Payload)!=0&&handoffCommitted.Load(){
                    goPostHandoffDataCopies.Add(1)
                }
                continue
            }
            outcome,e:=a.HandleSegment(seg,time.Now())
            if e!=nil{
                if !errors.Is(e,faketcp.ErrHandshakeState){
                    select{case failed<-e:default:}
                }
                continue
            }
            if outcome.AckNeeded{
                if e=emit(a.ACKSegment(outcome.Ack));e!=nil{
                    select{case failed<-e:default:};return
                }
            }
            flow:=a.Flow()
            if !seen[flow]&&a.State()==faketcp.ServerAssociationEstablished{
                seen[flow]=true
                select{case admitted<-a:default:}
            }
        }
    }()
    // Client opens lanes sequentially; after collection each still must
    // present its correct protected lane ID 1..n to AcceptServerGame.
    // Source port, NAT and SYN arrival order NEVER grant authorization.
    waitCtx,cancel:=context.WithTimeout(ctx,45*time.Second)
    defer cancel()
    for i:=range assocs{
        select{
        case a:=<-admitted:assocs[i]=a
        case err=<-failed:return err
        case <-waitCtx.Done():return waitCtx.Err()
        }
    }
    reply:=realityfront.ServerAdmissionConfig{
        TLS:realityfront.ServerConfig{
            ServerName:c.serverName,RouteKey:c.routeKey,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},
            Timeout:15*time.Second,
        },
        ExpectedUsername:c.username,ExpectedPassword:c.password,ServerLimit:c.recordLimit,
        AllocateLease:originalV4AutomaticLease(leases),
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            if len(req.TunnelID)!=16{return realityfront.ErrAdmissionParams}
            if req.AutoLease{
                if leases==nil{return realityfront.ErrAdmissionParams}
            }else if c.tunnel==[16]byte{}||string(req.TunnelID)!=string(c.tunnel[:]){
                return realityfront.ErrAdmissionParams
            }
            return nil
        },
    }
    admitCtx,cancelAdmission:=context.WithTimeout(ctx,60*time.Second)
    err=native.AcceptServerGame(admitCtx,assocs,reply)
    cancelAdmission()
    if err!=nil{_ = native.Close();return err}
    peers:=make([]faketcp.DetachedPeer,0,n)
    for i,a:=range assocs{
        if a==nil{
            _=native.Close()
            return fmt.Errorf("Game server lane %d missing at original M4 handoff",i+1)
        }
        state,exists:=a.TransitionState()
        if !exists||state!=faketcp.TransitionDetached{
            _=native.Close()
            return fmt.Errorf("Game server lane %d not detached at M4 handoff",i+1)
        }
        flow:=a.Flow()
        if flow.ServerIP!=c.localIP.As4()||flow.ServerPort!=c.localPort{
            _=native.Close()
            return fmt.Errorf("Game server lane %d escaped single-port tuple scope",i+1)
        }
        peers=append(peers,faketcp.DetachedPeer{IP:flow.ClientIP,Port:flow.ClientPort})
    }
    // Install the exact union once; a second SO_ATTACH_FILTER call for
    // another lane would silently re-expose the earlier native DATA to Go.
    if e:=raw.ExcludeDetachedDataSet(peers);e!=nil{
        _=native.Close()
        return fmt.Errorf("Game server shared-port kernel RX handoff: %w",e)
    }
    handoffCommitted.Store(true)
    log.Printf("V4_PUBLIC_GAME_SINGLE_SERVER_PORT role=server lanes=%d server_port=%d distinct_client_flows=%d",
        n,c.localPort,len(peers))
    log.Printf("V4_PUBLIC_GAME_GO_RX_HANDOFF role=server lanes=%d filtered=%d rust_ready=1 original_send_fd_open=1",n,n)
    *connected=true
    log.Printf("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=%d original_tls=1 rust_m4=1",n)
    if c.gameFecEnabled{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=fixed profile=%d auth_original_tls=1 original_M4=1",n,c.gameFecProfile)
    }else{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=off profile=0 auth_original_tls=1 original_M4=1",n)
    }
    select{case <-ctx.Done():case err=<-failed:}
    log.Printf("V4_PUBLIC_GAME_GO_RX_POST_HANDOFF role=server lanes=%d go_data_full_copies=%d",n,goPostHandoffDataCopies.Load())
    counters,countErr:=native.KernelCounters()
    if countErr==nil{
        log.Printf("V4_PUBLIC_GAME_KERNEL role=server lanes=%d copied=%d delivered=%d rejected=%d raw_received=%d auth_rejected=%d",
            n,counters.Copied,counters.Delivered,counters.Rejected,
            counters.RawReceived,counters.AuthenticatedRejected)
    }
    if errOuter:=logGameOuterRepair("server",n,native,c.disableOuterRepair);errOuter!=nil{
        err=errors.Join(err,errOuter)
    }
    if c.gameFecEnabled{logOriginalGameFec("server",n,native)}
    if n==4{
        if e:=logGame4CopySchedule("server",native,c.game4CopyStagger,c.game4CopyWideStagger);e!=nil{return e}
    }
    closeErr:=native.Close()
    if closeErr==nil{log.Printf("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=server lanes=%d",n)}
    return errors.Join(err,closeErr)
}


/*
PLAN028 H1037: one real Game2/4 server socket and original Go TLS policy,
many independently authenticated groups. All untrusted packets are still
delivered only to the original Go FakeTCP cold handler; native Rust owns
all detached DATA. No new transport, FEC or per-packet Go forwarding.
*/
// A protected epoch identifies the logical Game owner, not a cold attempt.
// After a lossy original TLS reply a former attempt may leave a single
// authenticated lane pending while a later generation starts with the SAME
// principal/tunnel/epoch. Grouping only by the protected owner could pair
// stale lane 1 with a new lane 2 and announce a false native M4 cohort.
// Original Linux and Windows Game2/4 clients bind n consecutive source
// ports for ONE attempt. Use that observed TCP tuple as an additional
// *joining constraint*, never as authentication or native owner authority.
type originalGameColdFlowKey struct {
    cohort realityfront.V4LinuxGameCohortID
    clientIP [4]byte
    serverIP [4]byte
    serverPort uint16
    firstClientPort uint16
}
func originalGameColdFlowIdentity(
    cohort realityfront.V4LinuxGameCohortID,id uint8,flow faketcp.ServerFlow,
)(originalGameColdFlowKey,error){
    n:=int(cohort.Lanes)
    ordinal:=int(id)
    first:=int(flow.ClientPort)-ordinal+1
    if (n!=2&&n!=4)||ordinal<1||ordinal>n||
        first<1||first+n-1>65535||flow.ServerPort==0 {
        return originalGameColdFlowKey{},realityfront.ErrAdmissionParams
    }
    return originalGameColdFlowKey{
        cohort:cohort,clientIP:flow.ClientIP,serverIP:flow.ServerIP,
        serverPort:flow.ServerPort,firstClientPort:uint16(first),
    },nil
}
type originalGameCohortPending struct{
    created time.Time
    lanes map[uint8]*realityfront.V4LinuxGameAuthenticatedLane
}
type originalGameCohortLive struct{
    key realityfront.V4LinuxGameCohortID
    product *realityfront.V4LinuxGameProduct
    members []*realityfront.V4LinuxGameAuthenticatedLane
    peers []faketcp.DetachedPeer
    gameFec bool // actual protected per-cohort Game fixed setting
    stopped bool
    laneRotations [4]uint64
}
func stageOriginalAuthenticatedGameLane(
    groups map[originalGameColdFlowKey]*originalGameCohortPending,
    lane *realityfront.V4LinuxGameAuthenticatedLane,now time.Time,
)(realityfront.V4LinuxGameCohortID,[]*realityfront.V4LinuxGameAuthenticatedLane,error){
    var zero realityfront.V4LinuxGameCohortID
    if lane==nil{return zero,nil,realityfront.ErrAdmissionParams}
    key,id,err:=lane.Cohort()
    if err!=nil{return zero,nil,err}
    n:=int(key.Lanes)
    if n!=2&&n!=4{return zero,nil,realityfront.ErrAdmissionUnsupported}
    // Different source-port generations MUST NOT share this pending slot,
    // even if their already-protected epoch and principal are identical.
    // A stale lane may expire independently without poisoning a fresh pair.
    cold,err:=originalGameColdFlowIdentity(key,id,lane.Association().Flow())
    if err!=nil{return key,nil,err}
    group:=groups[cold]
    if group==nil{
        group=&originalGameCohortPending{
            created:now,lanes:make(map[uint8]*realityfront.V4LinuxGameAuthenticatedLane,n),
        }
        groups[cold]=group
    }
    // A simultaneous same-identity successor carrying an already occupied
    // lane cannot be distinguished using SYN order. Reject the ambiguity,
    // NEVER mix old/new exporter incarnations into one GameAdapter.
    if group.lanes[id]!=nil{return key,nil,realityfront.ErrAdmissionParams}
    group.lanes[id]=lane
    if len(group.lanes)!=n{return key,nil,nil}
    ordered:=make([]*realityfront.V4LinuxGameAuthenticatedLane,n)
    for id:=1;id<=n;id++{
        if group.lanes[uint8(id)]==nil{return key,nil,realityfront.ErrAdmissionParams}
        ordered[id-1]=group.lanes[uint8(id)]
    }
    delete(groups,cold)
    return key,ordered,nil
}
func runGameMultiServer(
    ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,
    connected *bool,cert tls.Certificate,
)(retErr error){
    const maxLiveRustLanes=16 // Rust MAX_SESSIONS, includes candidates and successors
    const cohortTimeout=45*time.Second
    n:=int(c.gameLanes)
    autoPool:=c.leasePool.IsValid()
    manual:=c.manualClientLease4.IsValid()
    manualAccounts:=len(c.manualClientLeases4)>0
    // Authenticated static account reservations and a disjoint automatic
    // device pool coexist on one shared native TUN.
    if epochs==nil||
        (autoPool!=(leases!=nil))||
        (manual&&(autoPool||manualAccounts))||
        (!autoPool&&!manual&&!manualAccounts)||
        (!c.mixedModes&&n!=2&&n!=4)||
        (c.mixedModes&&(n!=0||manual||(!autoPool&&!manualAccounts))){
        return realityfront.ErrAdmissionParams
    }
    shared,err:=realityfront.NewV4LinuxSharedTun(tun.f,c.tunName)
    if err!=nil{return err}
    // The original Go Run() owns the underlying OS TUN until the final
    // Game group Stop and this one reader have both joined.
    defer func(){retErr=errors.Join(retErr,shared.Close())}()
    cfg:=realityfront.V4LinuxGameProductConfig{
        NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
        Tun:tun.f,TunName:c.tunName,SharedTun:shared,
        CleanupOwnedNetwork:func()error{return nil},
        // Shared TUN MTU is process-owned; one device cannot raise it while
        // another authenticated Game group is still using its old budget.
        ConfigureTunnelMTU:nil,
        GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
        DisableOuterRepair:c.disableOuterRepair,
        Game4CopyStagger:c.game4CopyStagger,
        Game4CopyWideStagger:c.game4CopyWideStagger,
        Epochs:epochs,PeerPersona:c.peerPersona,
        Authenticate:originalV4CredentialCheck(c),
        ServerManualLease4:func()string{if manual{return c.manualClientLease4.String()};return ""}(),
        ServerManualLeases4:c.manualClientLeases4,
    }
    rawPersona:=faketcp.PacketPersonaLegacy
    if c.peerPersona==realityfront.V4PeerWindows11{
        rawPersona=faketcp.PacketPersonaWindows11
    }
    raw,err:=faketcp.OpenRawIPv4EndpointWithOptions(
        c.rawInterface,c.localIP.As4(),rawPersona,
        faketcp.RawIPv4EndpointOptions{ReceivePort:c.localPort},
    )
    if err!=nil{return err}
    defer raw.Close()
    emit:=func(seg faketcp.Segment)error{_,e:=raw.WriteSegment(seg);return e}
    table,err:=faketcp.NewServerAssociationTable(32,emit)
    if err!=nil{return err}
    defer table.Close()
    runCtx,cancel:=context.WithCancel(ctx)
    defer cancel()
    base:=realityfront.ServerAdmissionConfig{
        TLS:realityfront.ServerConfig{
            ServerName:c.serverName,RouteKey:c.routeKey,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},
            Timeout:15*time.Second,
        },
        ExpectedUsername:c.username,ExpectedPassword:c.password,
        ServerLimit:c.recordLimit,
        AllocateLease:originalV4AutomaticLease(leases),
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            // Protected TLS alone may allocate the device's /32. A manual
            // tunnel, unauthenticated source tuple or a no-install ID cannot
            // enter the multi-group native shared TUN.
            if len(req.TunnelID)!=16{return realityfront.ErrAdmissionParams}
            if err:=originalV4SharedLeaseRequestAfterAuth(c,req,autoPool);err!=nil{return err}
            return nil
        },
    }
    type authResult struct{
        assoc *faketcp.ServerAssociation
        lane *realityfront.V4LinuxGameAuthenticatedLane
        err error
    }
    established:=make(chan *faketcp.ServerAssociation,32)
    authenticated:=make(chan authResult,32)
    failed:=make(chan error,1)
    var mu sync.Mutex
    seen:=make(map[*faketcp.ServerAssociation]bool,32)
    pending:=make(map[originalGameColdFlowKey]*originalGameCohortPending)
    active:=make(map[realityfront.V4LinuxGameCohortID]*originalGameCohortLive)
    // Normal and Game share THIS listener, table and native TUN reader.
    // Normal keys deliberately exclude epoch (successor replaces only same
    // principal+tunnel), Game keys retain the complete protected cohort.
    activeNormal:=make(map[realityfront.V4LinuxGameCohortID]*originalV4MultiRecord)
    // Normal B is a COLD authenticated candidate, NOT the active per-/32
    // server route. Only this event loop publishes the exact B after its
    // own native M4 observes an authenticated client-B Health kind0.
    type normalProofResult struct{
        key realityfront.V4LinuxGameCohortID
        rec *originalV4MultiRecord
        err error
    }
    normalPending:=make(map[realityfront.V4LinuxGameCohortID]*originalV4MultiRecord)
    normalProofReady:=make(chan normalProofResult,32)
    // Same cold-only readiness fence for Game2/4 whole-group replacement.
    // Hot Game4 single-lane swap never uses this group-level route.
    type gameProofResult struct{
        key realityfront.V4LinuxGameCohortID
        rec *originalGameCohortLive
        err error
    }
    gameProofPending:=make(map[realityfront.V4LinuxGameCohortID]*originalGameCohortLive)
    gameProofReady:=make(chan gameProofResult,32)
    detached:=make(map[*faketcp.ServerAssociation]faketcp.DetachedPeer)
    // Already switched Game4 slots keep the old cold association/port
    // excluded from Go DATA until its bounded random retirement deadline.
    hotRetiring:=make(map[*faketcp.ServerAssociation]time.Time)
    // A new authentic M4 /32 succeeds before the server retires its old
    // generation; preserve the previous Rust RX for random 10-20s.
    // Exact old Stop remains immediate when the whole server closes.
    type oldGameRetirement struct{group *originalGameCohortLive; due time.Time}
    type oldNormalRetirement struct{rec *originalV4MultiRecord; due time.Time}
    var gameRetiring []oldGameRetirement
    var normalRetiring []oldNormalRetirement
    // Error-only, once per exact cold association: a 64-record staged
    // burst is not an auth error, while malformed sequence remains fatal.
    // Delete on forget so long-lived shared-port servers stay bounded.
    var preDetachFaultSeen sync.Map
    var tlsWG sync.WaitGroup
    var goPostHandoffDataCopies atomic.Uint64
    var stopping atomic.Bool
    peers:=func(extra []faketcp.DetachedPeer)[]faketcp.DetachedPeer{
        out:=make([]faketcp.DetachedPeer,0,len(detached)+len(extra))
        for _,p:=range detached{out=append(out,p)}
        return append(out,extra...)
    }
    forget:=func(a *faketcp.ServerAssociation){
        if a==nil{return}
        mu.Lock();delete(seen,a);mu.Unlock()
        preDetachFaultSeen.Delete(a)
        table.Remove(a.Flow())
    }
    rejectLane:=func(l *realityfront.V4LinuxGameAuthenticatedLane){
        if l==nil{return}
        if err:=l.Close();err!=nil{
            select{case failed<-fmt.Errorf("Game incomplete original TLS Stop: %w",err):default:}
        }
        forget(l.Association())
    }
    retire:=func(rec *originalGameCohortLive,reason string)error{
        if rec==nil||rec.stopped{return nil}
        // Cold readback of this exact authenticated group's real M4 FEC
        // counters precedes owned Stop; do not aggregate siblings.
        if rec.gameFec{logOriginalGameFec("server",int(rec.key.Lanes),rec.product)}
        if err:=rec.product.Close();err!=nil{
            return fmt.Errorf("Game group native Stop reason=%s: %w",reason,err)
        }
        rec.stopped=true
        for _,l:=range rec.members{
            delete(detached,l.Association())
            forget(l.Association())
        }
        if remaining:=peers(nil);len(remaining)>0{
            if err:=raw.ExcludeDetachedDataSet(remaining);err!=nil{return err}
        }else{
            // The LAST authenticated native Game group is fully stopped:
            // restore the original listener port filter, not the stale
            // detached tuple filter. A NAT may reuse the same TCP 4-tuple
            // for a completely fresh genuine TLS bootstrap.
            if err:=raw.RestoreOriginalBootstrapPortFilter();err!=nil{return err}
        }
        log.Printf("V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=%s remaining_flows=%d",
            reason,len(detached))
        return nil
    }
    retireNormal:=func(rec *originalV4MultiRecord,reason string)error{
        if rec==nil||rec.product==nil||!rec.ready||rec.stopping{return nil}
        if actual,e:=rec.product.OriginalFECReadback();e==nil{
            log.Printf("V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=%s profile=%d requested=%d applied=%d",
                actual.Mode,actual.Profile,actual.RequestedRevision,actual.AppliedRevision)
        }
        if e:=rec.product.Close();e!=nil{
            return fmt.Errorf("mixed Normal generation native Stop %s: %w",reason,e)
        }
        rec.stopping=true
        delete(detached,rec.assoc)
        forget(rec.assoc)
        if len(detached)>0{
            if e:=raw.ExcludeDetachedDataSet(peers(nil));e!=nil{return e}
        }else if e:=raw.RestoreOriginalBootstrapPortFilter();e!=nil{return e}
        log.Printf("V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=%s remaining_flows=%d",
            reason,len(detached))
        return nil
    }
    scheduleGameRetire:=func(group *originalGameCohortLive){
        if group==nil{return}
        grace:=originalLaneRetirementGrace()
        gameRetiring=append(gameRetiring,oldGameRetirement{group,time.Now().Add(grace)})
        log.Printf("V4_PUBLIC_GAME_OLD_SERVER_RETIRE_SCHEDULED role=server lanes=%d grace_ms=%d old_m4_rx_preserved=1",group.key.Lanes,grace.Milliseconds())
    }
    scheduleNormalRetire:=func(rec *originalV4MultiRecord){
        if rec==nil{return}
        grace:=originalLaneRetirementGrace()
        normalRetiring=append(normalRetiring,oldNormalRetirement{rec,time.Now().Add(grace)})
        log.Printf("V4_PUBLIC_NORMAL_OLD_SERVER_RETIRE_SCHEDULED role=server grace_ms=%d old_m4_rx_preserved=1",grace.Milliseconds())
    }
    defer func(){
        stopping.Store(true)
        cancel()
        tlsWG.Wait() // no TLS or cold B proof may outlive Stop
        for _,rec:=range normalPending{
            retErr=errors.Join(retErr,retireNormal(rec,"server-close-unproven-B"))
        }
        for _,group:=range gameProofPending{
            retErr=errors.Join(retErr,retire(group,"server-close-unproven-Game-B"))
        }
        for _,group:=range pending{
            for _,lane:=range group.lanes{rejectLane(lane)}
        }
        for _,group:=range active{
            if err:=retire(group,"server-close");err!=nil{
                retErr=errors.Join(retErr,err)
            }
        }
        for _,rec:=range activeNormal{
            if err:=retireNormal(rec,"server-close");err!=nil{
                retErr=errors.Join(retErr,err)
            }
        }
        for _,old:=range gameRetiring{
            retErr=errors.Join(retErr,retire(old.group,"server-close-during-grace"))
        }
        for _,old:=range normalRetiring{
            retErr=errors.Join(retErr,retireNormal(old.rec,"server-close-during-grace"))
        }
        *connected=*connected||len(active)>0||len(activeNormal)>0
    }()
    go func(){
        for{
            seg,_,e:=raw.ReadSegment()
            if e!=nil{
                if runCtx.Err()==nil{
                    select{case failed<-e:default:}
                }
                return
            }
            if seg.DstPort!=c.localPort{continue}
            if faketcp.IsInitialSYN(seg){
                if !seg.MSSSet||seg.MSS<536||seg.MSS>1460{continue}
                isn,e:=originalRandomISN()
                if e!=nil{select{case failed<-e:default:};return}
                a,e:=table.AddSYN(seg,isn,time.Second)
                if errors.Is(e,faketcp.ErrAssociationExists){continue}
                if e!=nil{continue} // cold table full, never evict live native
                synack,e:=a.SYNACKSegment()
                if e==nil{e=emit(synack)}
                if e!=nil{select{case failed<-e:default:};return}
                continue
            }
            a,ok:=table.GetSegment(seg)
            if !ok||a.State()==faketcp.ServerAssociationClosed{continue}
            if state,exists:=a.TransitionState();exists&&
               state==faketcp.TransitionDetached{
                if len(seg.Payload)>0{goPostHandoffDataCopies.Add(1)}
                continue
            }
            outcome,e:=a.HandleSegment(seg,time.Now())
            if e!=nil{
                kind:=""
                switch{
                case errors.Is(e,faketcp.ErrTransitionOverflow):kind="bounded_pre_detach_data_overflow"
                case errors.Is(e,faketcp.ErrTransitionOverlap):kind="bootstrap_record_boundary_overlap"
                case errors.Is(e,faketcp.ErrTransitionConflict):kind="same_sequence_payload_conflict"
                case errors.Is(e,faketcp.ErrTransitionRecordSize):kind="record_exceeds_wire_limit"
                case errors.Is(e,faketcp.ErrTransitionAborted):kind="already_aborted"
                }
                if kind!=""{
                    if _,logged:=preDetachFaultSeen.LoadOrStore(a,struct{}{});!logged{
                        state,exists:=a.TransitionState()
                        log.Printf("V4_PUBLIC_GAME_PRE_DETACH_ROUTE_ERROR role=server class=%s transition_state=%d state_exists=%t client_port=%d",
                            kind,state,exists,a.Flow().ClientPort)
                    }
                }
                continue
            }
            if outcome.AckNeeded{
                if e=emit(a.ACKSegment(outcome.Ack));e!=nil{
                    select{case failed<-e:default:};return
                }
            }
            if a.State()!=faketcp.ServerAssociationEstablished{continue}
            mu.Lock()
            if !stopping.Load()&&!seen[a]&&len(seen)<maxLiveRustLanes{
                seen[a]=true
                select{case established<-a:default:delete(seen,a)}
            }
            mu.Unlock()
        }
    }()
    if c.mixedModes{
        log.Printf("V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=%d policy=protected_normal_game2_game4 cold_slots=32 rust_native_slots=16 shared_rust_tun=1",c.localPort)
    }else{
        log.Printf("V4_PUBLIC_GAME_MULTI_SERVER_READY role=server port=%d lanes_per_group=%d cold_association_slots=32 rust_native_total_lane_slots=16 shared_rust_tun=1",
            c.localPort,n)
    }
    ticker:=time.NewTicker(time.Second)
    defer ticker.Stop()
    for{
        select{
        case <-runCtx.Done():return nil
        case e:=<-failed:return e
        case a:=<-established:
            if a==nil{continue}
            tlsWG.Add(1)
            go func(a *faketcp.ServerAssociation){
                defer tlsWG.Done()
                var lane *realityfront.V4LinuxGameAuthenticatedLane
                var e error
                if c.mixedModes{
                    lane,e=realityfront.V4AuthenticateLinuxMixedServerLane(
                        runCtx,a,base,cfg)
                }else{
                    lane,e=realityfront.V4AuthenticateLinuxGameServerLane(
                        runCtx,a,base,cfg,n)
                }
                select{
                case authenticated<-authResult{assoc:a,lane:lane,err:e}:
                case <-runCtx.Done():
                    if lane!=nil{_ = lane.Close()}
                }
            }(a)
        case result:=<-authenticated:
            if result.err!=nil{
                // The old generic REJECT hid the difference between a
                // 15s TLS timeout, a protected-policy refusal, and a native
                // cold Commit failure. Never print credentials/keys; log
                // only the observed source port and coarse failure class.
                port:=uint16(0)
                if result.assoc!=nil{port=result.assoc.Flow().ClientPort}
                stage:="protected_tls"
                switch{
                case errors.Is(result.err,realityfront.ErrV4ProtectedReplyAckWait):
                    stage="protected_reply_ack_wait"
                case errors.Is(result.err,realityfront.ErrV4ServerEpochReserve):
                    stage="protected_epoch_reserve"
                case errors.Is(result.err,realityfront.ErrV4ServerOwnerPrepare):
                    stage="native_m4_prepare"
                case errors.Is(result.err,realityfront.ErrV4ServerDetachTransition):
                    stage="protected_reply_detach"
                case errors.Is(result.err,realityfront.ErrV4ServerNativeCommit):
                    stage="native_m4_commit_after_reply"
                }
                log.Printf("V4_PUBLIC_GAME_MULTI_ADMISSION_REJECT stage=%s class=%s m4_substage=%s native_rc=%d client_port=%d",
                    stage,nativeColdFailureClass(result.err),
                    realityfront.V4OriginalNativeM4FailureStage(result.err),
                    realityfront.V4NormalM4NativeCode(result.err),port)
                forget(result.assoc)
                continue
            }
            lane:=result.lane
            normal,_,gameFec,modeErr:=lane.ProtectedMode()
            if modeErr!=nil{
                rejectLane(lane)
                continue
            }
            if normal{
                // A protected Normal singleton uses the SAME existing
                // original product M4 install after the shared TLS detach,
                // not a second listener or Go DATA path.
                key,e:=lane.NormalOwnerKey()
                if e!=nil{rejectLane(lane);continue}
                // Mixed one443 has Windows AND Linux original SYN styles.
                // Never apply one process-global NPF persona to every
                // independently authenticated Normal native Rust owner.
                actualPersona,personaKnown:=originalV4ColdAssocPeerPersona(
                    lane.Association(),c.peerPersona)
                normalCfg:=realityfront.V4LinuxServerProductConfig{
                    Epochs:epochs,NetworkInterface:c.rawInterface,
                    NetworkIfIndex:ifindex,Tun:tun.f,TunName:c.tunName,
                    SharedTun:shared,CleanupOwnedNetwork:func()error{return nil},
                    PerClientNormalFEC:true,FECMode:realityfront.FecV2Off,
                    FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
                    PeerPersona:actualPersona,Authenticate:originalV4CredentialCheck(c),
                }
                product,e:=realityfront.NewV4LinuxServerProduct(normalCfg)
                if e!=nil{rejectLane(lane);continue}
                session,e:=product.AdoptAuthenticatedNormalLane(lane)
                if e==nil{
                    log.Printf("V4_PUBLIC_MIXED_NORMAL_PEER_PERSONA role=server client_port=%d selected=%d cold_syn_known=%t authenticated_TLS=1 original_Rust_M4=1",
                        lane.Association().Flow().ClientPort,actualPersona,personaKnown)
                }
                if e!=nil{
                    _=product.Close()
                    rejectLane(lane)
                    // A client TLS/M4 local READY is not proof of the
                    // server's M4 install. This hard failure previously
                    // had no native substage or client port, masking an
                    // entire 73s source-locked healthy-TC outage. Do not
                    // log credentials or arbitrary error strings here.
                    port:=uint16(0)
                    peerIP:=[4]byte{}
                    if result.assoc!=nil{
                        flow:=result.assoc.Flow()
                        port=flow.ClientPort
                        peerIP=flow.ClientIP
                    }
                    log.Printf("V4_PUBLIC_MIXED_ADMISSION_REJECT stage=normal_rust_owner m4_stage=%s native_rc=%d class=%s client_ipv4=%d.%d.%d.%d client_port=%d",
                        realityfront.V4NormalM4FailureStage(e),
                        realityfront.V4NormalM4NativeCode(e),
                        nativeColdFailureClass(e),
                        peerIP[0],peerIP[1],peerIP[2],peerIP[3],port)
                    continue
                }
                lease,e:=session.AuthenticatedLeaseIPv4()
                peer,peerErr:=lane.DetachedPeer()
                if e!=nil||peerErr!=nil||lease==""{
                    _=product.Close()
                    return realityfront.ErrAdmissionParams
                }
                older:=activeNormal[key]
                if normalPending[key]!=nil{
                    // One cold B per authenticated logical Normal owner.
                    // Do not let a later TLS candidate supersede pending B
                    // or withdraw A while the first B proves real peer RX.
                    _=product.Close()
                    forget(result.assoc)
                    log.Printf("V4_PUBLIC_MIXED_NORMAL_B_REJECT reason=candidate_already_pending client_port=%d old_route_preserved=1",peer.Port)
                    continue
                }
                if e=raw.ExcludeDetachedDataSet(peers([]faketcp.DetachedPeer{peer}));e!=nil{
                    _=product.Close()
                    return fmt.Errorf("mixed Normal same-port kernel handoff: %w",e)
                }
                rec:=&originalV4MultiRecord{
                    assoc:result.assoc,product:product,lease:lease,
                    peer:peer,ready:true,
                }
                detached[result.assoc]=peer
                if older!=nil{
                    // Rust kept A's only /32 send route. Client B may be
                    // receiving this server's authenticated Health, but a
                    // local B TLS/M4 START is NOT proof of client B's native
                    // RX socket. Wait off this listener's event loop: a
                    // broken device must not block other accounts/Game.
                    normalPending[key]=rec
                    tlsWG.Add(1)
                    go func(k realityfront.V4LinuxGameCohortID,b *originalV4MultiRecord){
                        defer tlsWG.Done()
                        proofErr:=waitOriginalNativeServerClientM4Ready(runCtx,
                            b.product.OriginalLoopPulse,func()error{return nil},
                            5*time.Second)
                        select{
                        case normalProofReady<-normalProofResult{k,b,proofErr}:
                        case <-runCtx.Done():
                        }
                    }(key,rec)
                    log.Printf("V4_PUBLIC_MIXED_NORMAL_B_PENDING role=server client_port=%d old_route_preserved=1 authenticated_client_M4_required=1",
                        peer.Port)
                    continue
                }
                activeNormal[key]=rec
                *connected=true
                log.Printf("V4_PUBLIC_MIXED_NORMAL_READY role=server port=%d client_ipv4=%d.%d.%d.%d client_port=%d active_normal=%d active_game_groups=%d detached_flows=%d protected_TLS=1 Rust_M4=1",
                    c.localPort,peer.IP[0],peer.IP[1],peer.IP[2],peer.IP[3],peer.Port,len(activeNormal),len(active),len(detached))
                continue
            }
            // The existing protected Go TLS admission can return exactly
            // ONE replacement Game4 lane of a LIVE, same-epoch group.
            // Never stage it as a fresh four-lane cohort or replace siblings.
            coldKey,laneID,e:=lane.Cohort()
            if e!=nil{rejectLane(lane);continue}
            // The selected-slot hot-rekey branch applies ONLY to Game4.
            // Game2 has no per-slot hot swap: a real same-epoch replacement
            // is ALWAYS a fresh authenticated two-lane complete cohort.
            // Rejecting active Game2 here prevented physical A→B Gen2
            // server M4 admission despite client Gen2 READY/old exact Stop,
            // leaving genuine post-READY UDP with no recipient.
            // Game4 single-lane reauth explicitly offers an existing
            // protected Epoch; a fresh full-group first lane offers ZERO.
            // Server-returned epochs are equal for both and cannot tell
            // them apart. Once a full group has begun, its remaining
            // explicit-epoch lanes must JOIN pending, not hot-swap A.
            // Physical IP/MTU changes remain an independent full-group hint.
            freshGroup,e:=lane.ProtectedFreshGroupRequested()
            if e!=nil{rejectLane(lane);continue}
            fullGroupPending:=false
            for candidate:=range pending{
                if candidate.cohort==coldKey{fullGroupPending=true;break}
            }
            if freshGroup&&coldKey.Lanes==4{
                log.Printf("V4_PUBLIC_GAME_FULL_GROUP_PROTECTED_EPOCH_ZERO role=server lane=%d client_port=%d old_group_preserved=1",
                    laneID,lane.Association().Flow().ClientPort)
            }
            if fullGroupPending&&coldKey.Lanes==4{
                log.Printf("V4_PUBLIC_GAME_FULL_GROUP_PENDING_JOIN role=server lane=%d client_port=%d old_group_preserved=1",
                    laneID,lane.Association().Flow().ClientPort)
            }
            if group:=active[coldKey];group!=nil&&coldKey.Lanes==4&&
                !freshGroup&&!fullGroupPending{
                if laneID<1||laneID>4{
                    rejectLane(lane)
                    continue
                }
                idx:=int(laneID)-1
                previous:=group.members[idx]
                if previous==nil{
                    rejectLane(lane)
                    continue
                }
                // A new complete A→B physical Game4 generation shares the
                // authenticated principal/tunnel/EPOCH with the old group.
                // It is NOT a one-lane hot swap just because its first TLS
                // lane arrives while the old cohort is still active.
                // Distinguish using the independently observed real TCP
                // source IP and the AUTHENTICATED cold record/MSS budgets,
                // never a client-supplied unprotected path-change flag.
                newFlow:=lane.Association().Flow()
                oldFlow:=previous.Association().Flow()
                oldCL,oldSL,eOld:=previous.AuthenticatedRecordLimits()
                newCL,newSL,eNew:=lane.AuthenticatedRecordLimits()
                if eOld!=nil||eNew!=nil{
                    rejectLane(lane)
                    continue
                }
                physicalGroupCandidate:=
                    newFlow.ClientIP!=oldFlow.ClientIP||
                    newFlow.ServerIP!=oldFlow.ServerIP||
                    newFlow.ServerPort!=oldFlow.ServerPort||
                    newCL!=oldCL||newSL!=oldSL
                if physicalGroupCandidate{
                    log.Printf("V4_PUBLIC_GAME_PHYSICAL_GROUP_CANDIDATE role=server lane=%d mode=authenticated_new_source_or_record_budget same_epoch=1 old_group_untouched=1",
                        laneID)
                    // Fall through into the EXISTING four-lane complete
                    // cohort staging below. Only after all four original
                    // protected TLS/M1 owners commit can the old GameAdapter
                    // receive an exact Stop. One lane never retires it.
                }else{
                    if !group.product.MatchesProtectedGameFec(gameFec){
                        rejectLane(lane)
                        continue
                    }
                    newPeer,e:=lane.DetachedPeer()
                    if e!=nil||newFlow.ServerIP!=c.localIP.As4()||
                        newFlow.ServerPort!=c.localPort{
                        rejectLane(lane)
                        continue
                    }
                    if e=raw.ExcludeDetachedDataSet(peers([]faketcp.DetachedPeer{newPeer}));e!=nil{
                        rejectLane(lane)
                        return fmt.Errorf("Game4 fresh one-lane TLS raw filter: %w",e)
                    }
                    if e=group.product.ReplaceServerGameLane(lane,laneID);e!=nil{
                        // A possibly partially committed native crypto/RX
                        // switch still fails closed: do not classify it as
                        // a harmless candidate rejection.
                        log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_NATIVE_REKEY_FAILED role=server class=uncertain_native_or_stop lane=%d",
                            laneID)
                        if err=retire(group,"one-lane-native-rekey-failed");err!=nil{return err}
                        delete(active,coldKey)
                        rejectLane(lane)
                        continue
                    }
                    oldAssoc:=previous.Association()
                    hotGrace:=originalLaneRetirementGrace()
                    hotRetiring[oldAssoc]=time.Now().Add(hotGrace)
                    log.Printf("V4_PUBLIC_GAME_OLD_COLD_TUPLE_RETIRE_SCHEDULED role=server lane=%d old_port=%d delay_ms=%d same_M4_slot=1",
                        laneID,oldAssoc.Flow().ClientPort,hotGrace.Milliseconds())
                    detached[lane.Association()]=newPeer
                    group.members[idx]=lane
                    group.peers[idx]=newPeer
                    group.laneRotations[idx]++
                    if e=raw.ExcludeDetachedDataSet(peers(nil));e!=nil{return e}
                    log.Printf("V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=%d rotation=%d client_port=%d server_port=%d same_game_adapter=1 sibling_lane_restarts=0 original_TLS=1 Rust_M4=1",
                        laneID,group.laneRotations[idx],newFlow.ClientPort,newFlow.ServerPort)
                    continue
                }
            }
            // A client M4 local READY cannot prove this second server
            // lane arrived. Make each independently protected arrival
            // visible so a missing Game2 cohort can be attributed to its
            // exact source port, rather than to a successful client banner.
            log.Printf("V4_PUBLIC_GAME_MULTI_PROTECTED_LANE_STAGED role=server lanes=%d lane=%d client_port=%d",
                coldKey.Lanes,laneID,lane.Association().Flow().ClientPort)
            key,complete,e:=stageOriginalAuthenticatedGameLane(
                pending,lane,time.Now(),
            )
            if e!=nil{
                rejectLane(lane)
                log.Printf("V4_PUBLIC_GAME_MULTI_ADMISSION_REJECT stage=cohort_identity")
                continue
            }
            if len(complete)==0{continue}
            gameCfg:=cfg
            if c.mixedModes {
                // A Game cohort is one authenticated logical device, but
                // each original lane SYN is independently observed. Select
                // one peer persona from known real SYN option layouts and
                // refuse a mixed-layout cohort instead of corrupting a
                // healthy sibling's Rust reader.
                selectedPersona:=c.peerPersona
                personaKnown:=false
                personaConflict:=false
                for _,member:=range complete{
                    peer,known:=originalV4ColdAssocPeerPersona(
                        member.Association(),selectedPersona)
                    if !known{continue}
                    if personaKnown&&peer!=selectedPersona{
                        personaConflict=true;break
                    }
                    selectedPersona=peer;personaKnown=true
                }
                if personaConflict{
                    for _,member:=range complete{rejectLane(member)}
                    log.Printf("V4_PUBLIC_MIXED_ADMISSION_REJECT stage=game_cohort_peer_persona")
                    continue
                }
                gameCfg.PeerPersona=selectedPersona
                log.Printf("V4_PUBLIC_GAME_MULTI_PEER_PERSONA role=server lanes=%d selected=%d cold_syn_known=%t authenticated_TLS=1 cohort=original_game",
                    key.Lanes,selectedPersona,personaKnown)
                // All lanes in this cohort must agree on the independently
                // protected Game fixed profile; no process-level FEC guess.
                var selected uint8
                matching:=true
                for i,member:=range complete{
                    memberNormal,memberLanes,gameFec,e:=member.ProtectedMode()
                    if e!=nil||memberNormal||memberLanes!=key.Lanes||
                        (i!=0&&gameFec!=selected){
                        matching=false
                        break
                    }
                    selected=gameFec
                }
                if !matching {
                    for _,l:=range complete{rejectLane(l)}
                    log.Printf("V4_PUBLIC_MIXED_ADMISSION_REJECT stage=game_cohort_fec")
                    continue // reject only the malformed cohort, never siblings
                }
                gameCfg.GameFecEnabled=selected>0
                if selected>0{gameCfg.GameFecProfile=selected-1}
                gameCfg.Game4CopyStagger=key.Lanes==4
                gameCfg.Game4CopyWideStagger=key.Lanes==4
            }
            product,e:=realityfront.NewV4LinuxGameServerProduct(gameCfg)
            if e!=nil{
                for _,l:=range complete{rejectLane(l)}
                continue
            }
            e=product.AdoptServerGameLanes(complete)
            if e!=nil{
                _=product.Close()
                for _,l:=range complete{rejectLane(l)}
                log.Printf("V4_PUBLIC_GAME_MULTI_ADMISSION_REJECT stage=game_owner")
                continue
            }
            // Existing native Game M4 effective policy, checked on THIS
            // authenticated group before its new generation becomes READY.
            if e=logGameOuterRepair("server",int(key.Lanes),product,c.disableOuterRepair);e!=nil{
                _=product.Close()
                return fmt.Errorf("shared Game original Rust outer readback: %w",e)
            }
            // Original dedicated server emits the protected Game FEC
            // receipt after real Rust M4 install. Same original receipt
            // per shared cohort, never a pre-TLS or CLI-only claim.
            if gameCfg.GameFecEnabled{
                if _,e=product.FecCounters();e!=nil{
                    _=product.Close()
                    return fmt.Errorf("shared Game native FEC install readback: %w",e)
                }
                log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=fixed profile=%d auth_original_tls=1 original_M4=1",
                    key.Lanes,gameCfg.GameFecProfile)
            }else{
                log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=off profile=0 auth_original_tls=1 original_M4=1",
                    key.Lanes)
            }
            newPeers:=make([]faketcp.DetachedPeer,0,n)
            for _,member:=range complete{
                peer,e:=member.DetachedPeer()
                flow:=member.Association().Flow()
                if e!=nil||flow.ServerIP!=c.localIP.As4()||
                    flow.ServerPort!=c.localPort{
                    _=product.Close()
                    return realityfront.ErrAdmissionUnsupported
                }
                newPeers=append(newPeers,peer)
            }
            if e=raw.ExcludeDetachedDataSet(peers(newPeers));e!=nil{
                _=product.Close()
                return fmt.Errorf("Game multi-group shared-port DATA filter: %w",e)
            }
            rec:=&originalGameCohortLive{
                key:key,product:product,members:complete,peers:newPeers,
                gameFec:gameCfg.GameFecEnabled,
            }
            for i,l:=range complete{
                detached[l.Association()]=newPeers[i]
                flow:=l.Association().Flow()
                log.Printf("V4_PUBLIC_GAME_GROUP_LANE_READY role=server lanes=%d lane=%d client_port=%d server_port=%d protected_TLS=1 original_Rust_M4=1 grouped_commit=1",
                    key.Lanes,i+1,flow.ClientPort,flow.ServerPort)
            }
            // Game B's grouped local TLS and M4 are not client-B RX proof.
            // Preserve the currently authenticated A /32 until this exact
            // candidate's client Health is AEAD/PN verified on server M4.
            // The old B remains the only TUN sender, and its RX grace is
            // unchanged. Do not tie Game4 hot one-lane rekeys to this gate.
            duplicatePending:=false
            for existing:=range gameProofPending{
                if existing.Principal==key.Principal&&existing.TunnelID==key.TunnelID{
                    duplicatePending=true;break
                }
            }
            if duplicatePending{
                if err:=retire(rec,"Game-B-already-pending");err!=nil{return err}
                log.Printf("V4_PUBLIC_GAME_B_REJECT role=server reason=candidate_pending old_route_preserved=1")
                continue
            }
            hasA:=false
            for oldKey:=range active{
                if oldKey.Principal==key.Principal&&oldKey.TunnelID==key.TunnelID{
                    hasA=true;break
                }
            }
            if hasA{
                gameProofPending[key]=rec
                tlsWG.Add(1)
                go func(k realityfront.V4LinuxGameCohortID,b *originalGameCohortLive){
                    defer tlsWG.Done()
                    proofErr:=waitOriginalNativeServerClientM4Ready(runCtx,
                        func()(realityfront.V4PublicLoopPulse,error){
                            counters,err:=b.product.KernelCounters()
                            if err!=nil{return realityfront.V4PublicLoopPulse{},err}
                            return realityfront.V4PublicLoopPulse{
                                AuthenticatedPeerControl:counters.AuthenticatedPeerControl,
                            },nil
                        },func()error{return nil},5*time.Second)
                    select{
                    case gameProofReady<-gameProofResult{k,b,proofErr}:
                    case <-runCtx.Done():
                    }
                }(key,rec)
                log.Printf("V4_PUBLIC_GAME_SERVER_B_PENDING role=server lanes=%d client_port=%d old_route_preserved=1 authenticated_client_M4_required=1",
                    key.Lanes,newPeers[0].Port)
                continue
            }
            active[key]=rec
            *connected=true
            log.Printf("V4_PUBLIC_GAME_SINGLE_SERVER_PORT role=server lanes=%d server_port=%d distinct_client_flows=%d",
                key.Lanes,c.localPort,len(detached))
            log.Printf("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=%d original_tls=1 rust_m4=1",key.Lanes)
            log.Printf("V4_PUBLIC_GAME_MULTI_GROUP_READY role=server server_port=%d groups=%d detached_flows=%d native_shared_tun=1",
                c.localPort,len(active),len(detached))
        case proof:=<-gameProofReady:
            rec:=gameProofPending[proof.key]
            if rec==nil||rec!=proof.rec{continue}
            delete(gameProofPending,proof.key)
            if proof.err!=nil||runCtx.Err()!=nil{
                log.Printf("V4_PUBLIC_GAME_SERVER_B_UNPROVEN role=server lanes=%d old_route_preserved=1 class=%s",
                    proof.key.Lanes,nativeColdFailureClass(proof.err))
                if err:=retire(rec,"client-Game-B-M4-unproven");err!=nil{return err}
                continue
            }
            if err:=rec.product.PromoteServerGameAfterAuthenticatedClientRx();err!=nil{
                log.Printf("V4_PUBLIC_GAME_SERVER_B_PROMOTE_REJECT role=server lanes=%d old_route_preserved=1",proof.key.Lanes)
                if stopErr:=retire(rec,"client-Game-B-M4-proof-rejected");stopErr!=nil{return stopErr}
                continue
            }
            // One event-loop owner publishes the exact confirmed B. Later
            // Stop of A is generation-fenced in the existing shared TUN.
            olderSameEpoch:=active[proof.key]
            active[proof.key]=rec
            *connected=true
            if olderSameEpoch!=nil{scheduleGameRetire(olderSameEpoch)}
            log.Printf("V4_PUBLIC_GAME_SERVER_B_CLIENT_READY role=server lanes=%d source=authenticated_client_native_Health promoted=1 old_route_preserved_until_proof=1",
                proof.key.Lanes)
            for oldKey,oldGroup:=range active{
                if oldKey==proof.key||oldKey.Principal!=proof.key.Principal||
                    oldKey.TunnelID!=proof.key.TunnelID{continue}
                scheduleGameRetire(oldGroup)
                delete(active,oldKey)
            }
        case proof:=<-normalProofReady:
            rec:=normalPending[proof.key]
            if rec==nil||rec!=proof.rec{continue}
            delete(normalPending,proof.key)
            if proof.err!=nil||runCtx.Err()!=nil{
                // B timeout/terminal only returns B's resources. A remains
                // the unique live /32 until its OWN native Health expires.
                log.Printf("V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN role=server client_port=%d old_route_preserved=1 class=%s",
                    rec.peer.Port,nativeColdFailureClass(proof.err))
                if e:=retireNormal(rec,"client-B-M4-unproven");e!=nil{return e}
                continue
            }
            // The proof worker only polls: the actual Rust publication
            // happens here after checking the exact current candidate.
            // No stale B may publish after replacement or final Stop.
            if e:=rec.product.PromoteNormalServerAfterAuthenticatedPeerRx();e!=nil{
                log.Printf("V4_PUBLIC_MIXED_NORMAL_B_PROMOTE_REJECT role=server client_port=%d old_route_preserved=1",rec.peer.Port)
                if stopErr:=retireNormal(rec,"client-B-M4-proof-rejected");stopErr!=nil{return stopErr}
                continue
            }
            older:=activeNormal[proof.key]
            activeNormal[proof.key]=rec
            *connected=true
            log.Printf("V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server client_port=%d source=authenticated_client_native_Health promoted=1 active_normal=%d old_route_preserved_until_proof=1",
                rec.peer.Port,len(activeNormal))
            if older!=nil{scheduleNormalRetire(older)}
        case <-ticker.C:
            now:=time.Now()
            for i:=0;i<len(gameRetiring);{
                old:=gameRetiring[i]
                if now.Before(old.due){i++;continue}
                if e:=retire(old.group,"same-protected-cohort-grace-expired");e!=nil{return e}
                gameRetiring=append(gameRetiring[:i],gameRetiring[i+1:]...)
            }
            for i:=0;i<len(normalRetiring);{
                old:=normalRetiring[i]
                if now.Before(old.due){i++;continue}
                if e:=retireNormal(old.rec,"same-protected-normal-grace-expired");e!=nil{return e}
                normalRetiring=append(normalRetiring[:i],normalRetiring[i+1:]...)
            }
            table.Sweep(now)
            if e:=table.EmitRetransmitDue(now);e!=nil{return e}
            removedOld:=false
            for old,until:=range hotRetiring{
                if now.Before(until){continue}
                delete(hotRetiring,old)
                delete(detached,old)
                forget(old)
                removedOld=true
            }
            if removedOld{
                if len(detached)>0{
                    if e:=raw.ExcludeDetachedDataSet(peers(nil));e!=nil{return e}
                }else if e:=raw.RestoreOriginalBootstrapPortFilter();e!=nil{return e}
            }
            for key,group:=range pending{
                if now.Sub(group.created)<cohortTimeout{continue}
                delete(pending,key)
                for _,lane:=range group.lanes{rejectLane(lane)}
                log.Printf("V4_PUBLIC_GAME_MULTI_INCOMPLETE_GROUP_EXPIRED lane_slots=%d",len(group.lanes))
            }
            // The EXISTING authenticated Game M4 Health90 sets its
            // native stop bit. Retire exactly that group (and its own
            // /32/Go TCP tuples) without a second dead timer or sibling
            // interference. No unauthenticated FIN/RST can do this.
            for key,group:=range active{
                alive,e:=group.product.NativeM4Alive()
                if e!=nil{return e}
                if alive{continue}
                if e=retire(group,"authenticated-rust-game-health90");e!=nil{return e}
                delete(active,key)
            }
            for key,rec:=range activeNormal{
                pulse,e:=rec.product.OriginalLoopPulse()
                if e!=nil||!publicNativeHealthDead(pulse){continue}
                if e=retireNormal(rec,"authenticated-rust-normal-health90");e!=nil{return e}
                if activeNormal[key]==rec{delete(activeNormal,key)}
            }
        }
    }
}
