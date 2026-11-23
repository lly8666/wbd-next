//go:build android && cgo && wbd_v4_embedded_go

package v4productcli

// B41 original Android Game2/off product: two real Bionic-network-bound
// FakeTCP/TLS lanes → one original Rust GameAdapter/M3/M4. The Go receiver
// handles ONLY the cold TLS association; original Rust owns every DATA.
import (
    "context"
    "errors"
    "fmt"
    "log"
    "net"
    "os"
    "os/exec"
    "sync"
    "sync/atomic"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
    "github.com/lly8666/wobuzhidao/internal/v4productcli/rstguard"
)

func androidGamePort(base uint16,lane int)(uint16,error){
    if lane<0||lane>3||int(base)+lane>65535||base==0{
        return 0,fmt.Errorf("original Android Game2/4 requires consecutive nonzero source ports")
    }
    return base+uint16(lane),nil
}
// Real original-Go Root cold entry. Only after both original TLS sessions,
// independent complete Detach and the shared Rust Game2 M4 reach Ready do
// ordinary Android app UID routes switch to the SAME protected /32.
func runAndroidGame(ctx context.Context,c config,ifindex uint32,
    tun *ownedTun,connected *bool,
)(retErr error){
    if (c.gameLanes!=2&&c.gameLanes!=4)||
       c.startupPaddingMode!=0||c.rotationInterval!=0||
       !c.autoIP||c.androidNetworkHandle==0||
       (c.gameLanes==4&&(!c.game4CopyStagger||!c.game4CopyWideStagger)){
        return fmt.Errorf("Android original Game2/4 requires padding/rotation off and wide Game4 stagger")
    }
    // Check the entire consecutive source-port group before any rule/socket.
    if _,e:=androidGamePort(c.localPort,int(c.gameLanes)-1);e!=nil{return e}
    if os.Geteuid()!=0{return fmt.Errorf("Android Game2 requires original root owned kernel")}
    iface,e:=net.InterfaceByName(c.rawInterface)
    if e!=nil||iface==nil||uint32(iface.Index)!=ifindex||
       uint32(iface.MTU)!=c.androidPhysicalMTU{
        return fmt.Errorf("original Game2 selected physical interface changed")
    }
    policy,e:=realityfront.PolicyForClientWithInitialAndCipher(
        int(c.gameLanes),"fixed",4,4,20,c.recordCipher)
    if e!=nil{return e}
    iptables,e:=exec.LookPath("iptables")
    if e!=nil{return fmt.Errorf("original Android Game2 exact RST guard unavailable")}
    runFirewall:=func(args ...string)(string,error){
        bounded,cancel:=context.WithTimeout(context.Background(),3*time.Second)
        defer cancel()
        out,err:=exec.CommandContext(bounded,iptables,args...).CombinedOutput()
        if len(out)>256<<10||err!=nil{
            return "",fmt.Errorf("original Game2 scoped firewall denied")
        }
        return string(out),nil
    }
    raws:=make([]*faketcp.RawIPv4Endpoint,0,int(c.gameLanes))
    assocs:=make([]*faketcp.ClientAssociation,0,int(c.gameLanes))
    var guard *rstguard.Guard
    stopRTO:=make([]func()(uint64,error),0,int(c.gameLanes))
    coldCtx,cancelCold:=context.WithCancel(ctx)
    var readers sync.WaitGroup
    var ready atomic.Bool
    defer func(){
        cancelCold()
        for _,stop:=range stopRTO{
            // Idempotent original cold RTO join on ALL exit paths,
            // including a partial first/second FakeTCP SYN failure.
            _,_ = stop()
        }
        // The Go physical RAW readers have no authority after this point.
        // Closing the actual source sockets unblocks their kernel reads.
        for _,r:=range raws{retErr=errors.Join(retErr,r.Close())}
        readers.Wait()
        for _,a:=range assocs{a.Close()}
        if guard!=nil{
            if err:=guard.Close();err!=nil{
                retErr=errors.Join(retErr,fmt.Errorf("Game2 exact RST guard owned Stop failed"))
            }
        }
    }()
    // ONE durable scoped iptables rule covers ONLY the two original
    // consecutive Game2 source ports, never all TCP or the root UID.
    // The legacy Root Restore reads the very same rst-guard.json.
    guard,_,e=rstguard.New(runFirewall,
        "/data/local/tmp/wbd-next-root/rst-guard.json",rstguard.Plan{
        Version:1,Interface:c.rawInterface,
        SourceIP:c.localIP.String(),PeerIP:c.peerIP.String(),
        SourcePort:int(c.localPort),PeerPort:int(c.peerPort),
        Game2:c.gameLanes==2,Game4:c.gameLanes==4,
    })
    if e!=nil{return fmt.Errorf("Game2 two-port exact RST guard: %w",e)}
    for lane:=0;lane<int(c.gameLanes);lane++{
        local,e:=androidGamePort(c.localPort,lane)
        if e!=nil{return e}
        raw,e:=faketcp.OpenRawIPv4EndpointWithOptions(
            c.rawInterface,c.localIP.As4(),faketcp.PacketPersonaLegacy,
            faketcp.RawIPv4EndpointOptions{ReceivePort:local})
        if e!=nil{return e}
        raws=append(raws,raw)
        if e=raw.BindAndroidNetwork(c.androidNetworkHandle,
            c.rawInterface,iface.Index,iface.MTU);e!=nil{return e}
        flow:=faketcp.ClientFlow{
            LocalIP:c.localIP.As4(),PeerIP:c.peerIP.As4(),
            LocalPort:local,PeerPort:c.peerPort,
        }
        isn,e:=originalRandomISN()
        if e!=nil{return e}
        assoc,e:=faketcp.NewClientAssociation(flow,isn,time.Second,
            func(seg faketcp.Segment)error{
                _,err:=raw.WriteSegment(seg)
                return err
            })
        if e!=nil{return e}
        assocs=append(assocs,assoc)
        readers.Add(1)
        go func(a *faketcp.ClientAssociation,r *faketcp.RawIPv4Endpoint,
            flow faketcp.ClientFlow){
            defer readers.Done()
            for{
                seg,_,err:=r.ReadSegment()
                if err!=nil{
                    // After original M4 READY and explicit quiesce, this
                    // receiver never owns authenticated DATA or reconnection.
                    select{case <-coldCtx.Done():return;default:}
                    if ready.Load(){return}
                    return
                }
                if !flow.MatchesInbound(seg){continue}
                if a.State()!=faketcp.ClientAssociationDetached{
                    _=a.HandleSegment(seg,time.Now())
                }
            }
        }(assoc,raw,flow)
        if e=assoc.Start(time.Now());e!=nil{return e}
        synCtx,cancel:=context.WithTimeout(ctx,20*time.Second)
        e=waitForOriginalColdSYN(synCtx,assoc)
        cancel()
        if e!=nil{return e}
        stopRTO=append(stopRTO,driveOriginalClientColdBootstrapRTO(coldCtx,assoc))
    }
    log.Printf("V4_PUBLIC_ANDROID_GAME_COLD_SOURCE role=client lanes=%d physical_network_bound=1 fake_tcp=original_go",c.gameLanes)
    // Real original-Go protected TLS on each of the TWO independent lanes,
    // then exact Rust B39 grouped cold + B40 M4 activation.
    var cn8503Raw []byte
    if c.androidCNDNSSplit{
        if c.androidCNSnapshot==nil{
            return fmt.Errorf("original Game2 CN8503 cold source absent")
        }
        cn8503Raw=c.androidCNSnapshot.PinnedWire()
    }
    native,e:=realityfront.NewV4AndroidGameProduct(
        realityfront.V4AndroidGameConfig{
            Lanes:c.gameLanes,
            GameFecEnabled:c.gameFecEnabled,GameFecProfile:c.gameFecProfile,
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            AndroidPhysicalNetworkHandle:c.androidNetworkHandle,
            AndroidPhysicalMTU:c.androidPhysicalMTU,
            Tun:tun.f,TunName:c.tunName,
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            ConfigureLeaseIPv4:configureAuthenticatedClientIPv4(tun),
            TunnelDNS:c.androidTunnelDNS,
            HealthSeconds:c.androidNativeHealthSeconds,
            PhysicalDNS:c.androidPhysicalDNS,
            PhysicalDNSUpstream:c.androidPhysicalDNSUpstream,
            CN8503Raw:cn8503Raw,
        })
    if e!=nil{return e}
    var undoRoute func()error
    defer func(){
        // Original group Stop MUST join M4 and all RAW loan borrows
        // BEFORE revoking this product's UID route/physical source.
        closeErr:=native.Close()
        retErr=errors.Join(retErr,closeErr)
        if closeErr==nil&&undoRoute!=nil{
            retErr=errors.Join(retErr,undoRoute())
        }
    }()
    admission:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{
            ServerName:c.serverName,RouteKey:c.routeKey,
            VerifyServer:c.tlsVerifyServer,RootCAs:c.tlsRoots,
            Timeout:15*time.Second,
        },
        Username:c.username,Password:c.password,
        TunnelID:c.tunnel[:],AutoLease:true,InstallationID:c.installation[:],
        ClientLimit:c.recordLimit,DesiredLanes:c.gameLanes,Policy:policy,
    }
    tlsCtx,cancelTLS:=context.WithTimeout(ctx,60*time.Second)
    lease,e:=native.ConnectAuthenticatedGame(tlsCtx,assocs,admission)
    cancelTLS()
    for _,stop:=range stopRTO{
        _,stopErr:=stop()
        e=errors.Join(e,stopErr)
    }
    if e!=nil{return e}
    for i,a:=range assocs{
        if a.State()!=faketcp.ClientAssociationDetached{
            return fmt.Errorf("original Android Game2 TLS lane%d not detached",i+1)
        }
    }
    ready.Store(true)
    for i,raw:=range raws{
        if e=raw.QuiesceDetachedClientReceive();e!=nil{
            return fmt.Errorf("original Android Game2 Go-Rust RAW RX handoff lane%d: %w",i+1,e)
        }
    }
    repeatOriginalDetachedTLSFinalACK(coldCtx,assocs...)
    if c.androidRouteAllApps||c.androidRouteUID!=0||len(c.androidRouteUIDs)>0{
        undoRoute,e=androidRootRouteAfterNative(c,tun,lease)
        if e!=nil{
            return fmt.Errorf("original Android Game2 authenticated UID FIB: %w",e)
        }
    }
    *connected=true
    log.Printf("V4_ORIGINAL_ANDROID_GAME_NATIVE_READY role=client lanes=%d original_go_tls=1 original_rust_m4=1 uid_route_after_m4=1",c.gameLanes)
    if c.gameFecEnabled{
        log.Printf("V4_PUBLIC_ANDROID_GAME_FEC_APPLIED role=client lanes=%d mode=fixed profile=%d original_tls=1 original_rust_m4=1",
            c.gameLanes,c.gameFecProfile)
    }
    ticker:=time.NewTicker(realityfront.V4AndroidGameStatusInterval)
    defer ticker.Stop()
    for{
        select{
        case <-ctx.Done():return nil
        case <-ticker.C:
            lanes,active,e:=native.OriginalNativeState()
            if e!=nil{return e}
            if lanes!=uint32(c.gameLanes)||!active{
                return fmt.Errorf("original Android Game2 M3/M4 worker stopped")
            }
            log.Printf("V4_PUBLIC_ANDROID_GAME_LANES role=client requested=%d native=%d active=%t",
                c.gameLanes,lanes,active)
            if c.gameFecEnabled{
                fec,e:=native.OriginalGameFecCounters()
                if e!=nil{return e}
                log.Printf("V4_PUBLIC_ANDROID_GAME_FEC_COUNTERS role=client lanes=%d profile=%d source=%d parity=%d copied=%d recovered=%d expired=%d failed=%d",
                    c.gameLanes,c.gameFecProfile,fec.SourceOffered,fec.ParityOffered,
                    fec.ParityKernelCopied,fec.RecoveredCandidate,fec.Expired,fec.Failed)
            }
            counters,e:=native.OriginalM4Counters()
            if e!=nil{return e}
            // Existing one-second status ticker, actual Rust M4.
            // Keep B43/B44 Game2 marker; distinguish real 4-lane readback.
            format:="V4_PUBLIC_ANDROID_GAME2_M4_COUNTERS role=client rawtx=%d rawrx=%d tun=%d rejected=%d dnstx=%d dnsrx=%d physicaltx=%d physicalrx=%d physicalerr=%d"
            if c.gameLanes==4{
                format="V4_PUBLIC_ANDROID_GAME4_M4_COUNTERS role=client rawtx=%d rawrx=%d tun=%d rejected=%d dnstx=%d dnsrx=%d physicaltx=%d physicalrx=%d physicalerr=%d"
            }
            log.Printf(format,
                counters.RawCopied,counters.RawReceived,counters.TunDelivered,
                counters.Rejected,counters.TunnelDnsQueries,counters.TunnelDnsReplies,
                counters.PhysicalDnsQueries,counters.PhysicalDnsReplies,counters.PhysicalDnsErrors)
        }
    }
}
