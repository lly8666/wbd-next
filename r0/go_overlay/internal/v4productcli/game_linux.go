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
    "time"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)
func gamePort(base uint16,lane int)(uint16,error){
    value:=int(base)+lane
    if value<1||value>65535{return 0,fmt.Errorf("Game 2/4 per-lane FakeTCP port overflow")}
    return uint16(value),nil
}
func runGame(ctx context.Context,c config,ifindex uint32,tun *ownedTun,connected *bool)error{
    if c.gameLanes!=2&&c.gameLanes!=4{return realityfront.ErrAdmissionUnsupported}
    if c.role=="client"{return runGameClient(ctx,c,ifindex,tun,connected)}
    return runGameServer(ctx,c,ifindex,tun,connected)
}
func runGameClient(ctx context.Context,c config,ifindex uint32,tun *ownedTun,connected *bool)error{
    n:=int(c.gameLanes)
    policy,err:=realityfront.FixedPolicyForClient(int(c.gameLanes),4)
    if err!=nil{return err}
    raws:=make([]*faketcp.RawIPv4Endpoint,0,n)
    assocs:=make([]*faketcp.ClientAssociation,0,n)
    defer func(){
        for _,raw:=range raws{raw.Close()}
        for _,a:=range assocs{a.Close()}
    }()
    fail:=make(chan error,n)
    for i:=0;i<n;i++{
        local,err:=gamePort(c.localPort,i)
        if err!=nil{return err}
        remote,err:=gamePort(c.peerPort,i)
        if err!=nil{return err}
        raw,e:=faketcp.OpenRawIPv4EndpointWithOptions(
            c.rawInterface,c.localIP.As4(),faketcp.PacketPersonaLegacy,
            faketcp.RawIPv4EndpointOptions{ReceivePort:local},
        )
        if e!=nil{return e}
        raws=append(raws,raw)
        emit:=func(seg faketcp.Segment)error{_,e:=raw.WriteSegment(seg);return e}
        flow:=faketcp.ClientFlow{LocalIP:c.localIP.As4(),PeerIP:c.peerIP.As4(),
            LocalPort:local,PeerPort:remote}
        isn,e:=originalRandomISN()
        if e!=nil{return e}
        assoc,e:=faketcp.NewClientAssociation(flow,isn,time.Second,emit)
        if e!=nil{return e}
        assocs=append(assocs,assoc)
        go func(a *faketcp.ClientAssociation,r *faketcp.RawIPv4Endpoint,f faketcp.ClientFlow){
            for{
                seg,_,readErr:=r.ReadSegment()
                if readErr!=nil{
                    select{case <-ctx.Done():return;default:}
                    select{case fail<-readErr:default:}
                    return
                }
                if !f.MatchesInbound(seg){continue}
                if a.State()!=faketcp.ClientAssociationDetached{
                    if err:=a.HandleSegment(seg,time.Now());err!=nil&&
                       !errors.Is(err,faketcp.ErrClientDetached){
                        select{case fail<-err:default:}
                    }
                }
            }
        }(assoc,raw,flow)
        if e=assoc.Start(time.Now());e!=nil{return e}
        establish,cancel:=context.WithTimeout(ctx,20*time.Second)
        e=assoc.WaitEstablished(establish)
        cancel()
        if e!=nil{return e}
    }
    native,err:=realityfront.NewV4LinuxGameClientProduct(
        realityfront.V4LinuxGameProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,CleanupOwnedNetwork:tun.Close,
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
        })
    if err!=nil{return err}
    cfg:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{
            ServerName:c.serverName,RouteKey:c.routeKey,Timeout:15*time.Second,
        },
        Username:c.username,Password:c.password,TunnelID:c.tunnel[:],
        ClientLimit:c.recordLimit,DesiredLanes:c.gameLanes,Policy:policy,
    }
    dialCtx,cancel:=context.WithTimeout(ctx,60*time.Second)
    err=native.ConnectClientGame(dialCtx,assocs,cfg)
    cancel()
    if err!=nil{return err}
    *connected=true
    log.Printf("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=%d original_tls=1 rust_m4=1",n)
    if c.gameFecEnabled{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=%d mode=fixed profile=%d auth_original_tls=1 original_M4=1",n,c.gameFecProfile)
    }else{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=%d mode=off profile=0 auth_original_tls=1 original_M4=1",n)
    }
    select{case <-ctx.Done():case err=<-fail:}
    counters,countErr:=native.KernelCounters()
    if countErr==nil{
        log.Printf("V4_PUBLIC_GAME_KERNEL role=client lanes=%d copied=%d delivered=%d rejected=%d raw_received=%d auth_rejected=%d",
            n,counters.Copied,counters.Delivered,counters.Rejected,
            counters.RawReceived,counters.AuthenticatedRejected)
    }
    closeErr:=native.Close()
    if closeErr==nil{log.Printf("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=%d",n)}
    return errors.Join(err,closeErr)
}
func runGameServer(ctx context.Context,c config,ifindex uint32,tun *ownedTun,connected *bool)error{
    n:=int(c.gameLanes)
    cert,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    store,err:=realityfront.NewV4EpochStore(16)
    if err!=nil{return err}
    native,err:=realityfront.NewV4LinuxGameServerProduct(
        realityfront.V4LinuxGameProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,CleanupOwnedNetwork:tun.Close,
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
            Epochs:store,
        })
    if err!=nil{return err}
    raws:=make([]*faketcp.RawIPv4Endpoint,0,n)
    defer func(){for _,r:=range raws{r.Close()}}()
    assocs:=make([]*faketcp.ServerAssociation,n)
    admitted:=make(chan int,n)
    failed:=make(chan error,n)
    for i:=0;i<n;i++{
        port,e:=gamePort(c.localPort,i)
        if e!=nil{return e}
        raw,e:=faketcp.OpenRawIPv4EndpointWithOptions(
            c.rawInterface,c.localIP.As4(),faketcp.PacketPersonaLegacy,
            faketcp.RawIPv4EndpointOptions{ReceivePort:port},
        )
        if e!=nil{return e}
        raws=append(raws,raw)
        emit:=func(seg faketcp.Segment)error{_,e:=raw.WriteSegment(seg);return e}
        table,e:=faketcp.NewServerAssociationTable(32,emit)
        if e!=nil{return e}
        go func(slot int,listenPort uint16,r *faketcp.RawIPv4Endpoint,
            table *faketcp.ServerAssociationTable,emit faketcp.SegmentEmitter){
            seen:=false
            for{
                seg,_,readErr:=r.ReadSegment()
                if readErr!=nil{
                    select{case <-ctx.Done():return;default:}
                    select{case failed<-readErr:default:}
                    return
                }
                if seg.DstPort!=listenPort{continue}
                if faketcp.IsInitialSYN(seg){
                    if seen{continue}
                    isn,e:=originalRandomISN()
                    if e!=nil{select{case failed<-e:default:};return}
                    a,e:=table.AddSYN(seg,isn,time.Second)
                    if errors.Is(e,faketcp.ErrAssociationExists){continue}
                    if e!=nil{select{case failed<-e:default:};return}
                    reply,e:=a.SYNACKSegment()
                    if e==nil{e=emit(reply)}
                    if e!=nil{select{case failed<-e:default:};return}
                    continue
                }
                a,ok:=table.GetSegment(seg)
                if !ok||a.State()==faketcp.ServerAssociationClosed{continue}
                if state,exists:=a.TransitionState();exists&&
                   state==faketcp.TransitionDetached{continue}
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
                if !seen&&a.State()==faketcp.ServerAssociationEstablished{
                    seen=true;assocs[slot]=a
                    select{case admitted<-slot:default:}
                }
            }
        }(i,port,raw,table,emit)
    }
    ready:=make(map[int]bool,n)
    waitCtx,cancel:=context.WithTimeout(ctx,45*time.Second)
    defer cancel()
    for len(ready)<n{
        select{
        case i:=<-admitted: ready[i]=true
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
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            if len(req.TunnelID)!=16||string(req.TunnelID)!=string(c.tunnel[:]){
                return realityfront.ErrAdmissionParams
            }
            return nil
        },
    }
    admitCtx,cancelAdmission:=context.WithTimeout(ctx,60*time.Second)
    err=native.AcceptServerGame(admitCtx,assocs,reply)
    cancelAdmission()
    if err!=nil{return err}
    *connected=true
    log.Printf("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=%d original_tls=1 rust_m4=1",n)
    if c.gameFecEnabled{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=fixed profile=%d auth_original_tls=1 original_M4=1",n,c.gameFecProfile)
    }else{
        log.Printf("V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=%d mode=off profile=0 auth_original_tls=1 original_M4=1",n)
    }
    select{case <-ctx.Done():case err=<-failed:}
    counters,countErr:=native.KernelCounters()
    if countErr==nil{
        log.Printf("V4_PUBLIC_GAME_KERNEL role=server lanes=%d copied=%d delivered=%d rejected=%d raw_received=%d auth_rejected=%d",
            n,counters.Copied,counters.Delivered,counters.Rejected,
            counters.RawReceived,counters.AuthenticatedRejected)
    }
    closeErr:=native.Close()
    if closeErr==nil{log.Printf("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=server lanes=%d",n)}
    return errors.Join(err,closeErr)
}
