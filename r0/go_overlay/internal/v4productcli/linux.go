//go:build linux && cgo && wbd_v4_embedded_go

// Package v4productcli is the ORIGINAL-Go Linux command runtime for the
// genuine V4/TLS -> Rust M1/M3 generation -> M4 raw/TUN continuous owner.
//
// No V3 data or test-synthetic traffic is used. The existing old Go CLI
// remains unaffected. The first formal capability is Normal/off; Fixed,
// Auto and Game2/4 require separate real V4 native sender/receiver promotion.
package v4productcli

import (
    "context"
    "crypto/rand"
    "crypto/tls"
    "encoding/binary"
    "encoding/hex"
    "errors"
    "flag"
    "fmt"
    "log"
    "net"
    "net/netip"
    "os"
    "os/exec"
    "os/signal"
    "syscall"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

const tunSetIFF=0x400454ca

type config struct{
    role string
    rawInterface string
    localIP netip.Addr
    peerIP netip.Addr
    localPort uint16
    peerPort uint16
    tunName string
    tunCIDR string
    serverName string
    routeKey []byte
    tlsCert string
    tlsKey string
    username string
    password string
    tunnel [16]byte
    fecMode realityfront.FecV2Mode
    fecProfile realityfront.FecV2Profile
    gameLanes uint8
}
func parse(role string,args []string)(config,error){
    var c config
    c.role=role
    if role!="client"&&role!="server"{return c,fmt.Errorf("unknown role")}
    flags:=flag.NewFlagSet("wbd-v4-"+role,flag.ContinueOnError)
    iface:=flags.String("raw-interface","","real Linux underlay device")
    ip:=flags.String("local-ip","","underlay local IPv4")
    peer:=flags.String("peer-ip","","remote underlay IPv4 (client only)")
    port:=flags.Uint("local-port",0,"original FakeTCP local port")
    remotePort:=flags.Uint("peer-port",0,"remote FakeTCP port (client)")
    tunName:=flags.String("tun-name","wbdv40","owned original Linux TUN name")
    tunCIDR:=flags.String("tun-ipv4","","owned real TUN IPv4 CIDR")
    name:=flags.String("server-name","","original TLS recognized SNI")
    route:=flags.String("route-key-hex","","original protected TLS route key")
    cert:=flags.String("tls-cert","","original server TLS PEM")
    key:=flags.String("tls-key","","original server private PEM")
    user:=flags.String("username","","original protected admission user")
    pass:=flags.String("password","","original protected admission password")
    tunnel:=flags.String("tunnel-id","","original logical 16B hex tunnel id")
    mode:=flags.String("mode","normal","V4 normal, fec-fixed, fec-auto, game2, game4")
    profile:=flags.Uint("fec-profile",1,"FEC2 profile 0..6 for fixed; auto uses strong startup")
    if err:=flags.Parse(args);err!=nil{return c,err}
    switch *mode{
    case "normal":c.fecMode=realityfront.FecV2Off
    case "fec-fixed":c.fecMode=realityfront.FecV2Fixed
    case "fec-auto":c.fecMode=realityfront.FecV2Auto
    case "game2":c.gameLanes=2;c.fecMode=realityfront.FecV2Off
    case "game4":c.gameLanes=4;c.fecMode=realityfront.FecV2Off
    default:return c,fmt.Errorf("V4 mode %q not installed in native public owner",*mode)
    }
    if *profile>6{return c,fmt.Errorf("fec-profile must be 0..6")}
    c.fecProfile=realityfront.FecV2Profile(*profile)
    if *iface==""||len(*tunName)==0||len(*tunName)>15||
       *tunCIDR==""||*name==""||*user==""||*pass==""||
       *port==0||*port>65535||len(*route)<32{
        return c,fmt.Errorf("missing/invalid real original V4 TLS/raw/TUN settings")
    }
    parsed,err:=netip.ParseAddr(*ip)
    if err!=nil||!parsed.Is4(){return c,fmt.Errorf("local-ip requires IPv4")}
    c.localIP=parsed
    c.rawInterface=*iface
    c.localPort=uint16(*port)
    c.tunName=*tunName
    c.tunCIDR=*tunCIDR
    c.serverName=*name
    c.username=*user
    c.password=*pass
    c.routeKey,err=hex.DecodeString(*route)
    if err!=nil||len(c.routeKey)<16{return c,fmt.Errorf("invalid TLS route key")}
    tunnelRaw,err:=hex.DecodeString(*tunnel)
    if err!=nil||len(tunnelRaw)!=16{return c,fmt.Errorf("invalid tunnel-id")}
    copy(c.tunnel[:],tunnelRaw)
    if c.tunnel==[16]byte{}{return c,fmt.Errorf("empty logical tunnel id")}
    if role=="server"{
        if *cert==""||*key==""{return c,fmt.Errorf("tls-cert and tls-key required")}
        c.tlsCert=*cert;c.tlsKey=*key
    }else{
        parsed,err=netip.ParseAddr(*peer)
        if err!=nil||!parsed.Is4(){return c,fmt.Errorf("peer-ip requires IPv4")}
        c.peerIP=parsed
        if *remotePort==0||*remotePort>65535{return c,fmt.Errorf("peer-port invalid")}
        c.peerPort=uint16(*remotePort)
    }
    if _,err=netip.ParsePrefix(*tunCIDR);err!=nil{return c,fmt.Errorf("invalid tun-ipv4")}
    return c,nil
}
func runIP(args ...string)error{
    cmd:=exec.Command("ip",args...)
    output,err:=cmd.CombinedOutput()
    if err!=nil{return fmt.Errorf("owned Linux ip %v: %w %s",args,err,output)}
    return nil
}
type ownedTun struct{
    f *os.File
    name string
    cleaned bool
}
// Original kernel-owned /dev/net/tun FD, never a synthetic traffic adapter.
func openTun(name,cidr string)(*ownedTun,error){
    fd,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{return nil,err}
    var ifr [40]byte
    copy(ifr[:16],[]byte(name))
    binary.NativeEndian.PutUint16(ifr[16:18],0x1001) // IFF_TUN | IFF_NO_PI
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,fd.Fd(),tunSetIFF,
        uintptr(unsafe.Pointer(&ifr[0])))
    if errno!=0{_ = fd.Close();return nil,errno}
    device:=&ownedTun{f:fd,name:name}
    if err=runIP("addr","add",cidr,"dev",name);err==nil{
        err=runIP("link","set","dev",name,"mtu","1200","up")
    }
    if err!=nil{_ = device.Close();return nil,err}
    return device,nil
}
func (d *ownedTun)Close()error{
    if d.cleaned{return nil}
    // Rust Stop must have returned before the product caller enters here.
    if err:=d.f.Close();err!=nil{return err}
    d.cleaned=true
    return nil // ephemeral TUN auto-deletes on last kernel FD close
}
func originalRandomISN()(uint32,error){
    var b [4]byte
    if _,err:=rand.Read(b[:]);err!=nil{return 0,err}
    n:=binary.BigEndian.Uint32(b[:])
    if n==0{return 1,nil}
    return n,nil
}
func Run(role string,args []string)error{
    cfg,err:=parse(role,args)
    if err!=nil{return err}
    iface,err:=net.InterfaceByName(cfg.rawInterface)
    if err!=nil{return err}
    tun,err:=openTun(cfg.tunName,cfg.tunCIDR)
    if err!=nil{return err}
    // This fallback is ONLY used if no authenticated Rust owner was started.
    // An active owner's Close performs Stop->release->network cleanup instead.
    connected:=false
    defer func(){if !connected {_ = tun.Close()}}()
    if cfg.gameLanes!=0{
        ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
        defer stop()
        return runGame(ctx,cfg,uint32(iface.Index),tun,&connected)
    }
    raw,err:=faketcp.OpenRawIPv4EndpointWithOptions(
        cfg.rawInterface,cfg.localIP.As4(),faketcp.PacketPersonaLegacy,
        faketcp.RawIPv4EndpointOptions{ReceivePort:cfg.localPort},
    )
    if err!=nil{return err}
    defer raw.Close()
    ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
    defer stop()
    emit:=func(seg faketcp.Segment)error{_,e:=raw.WriteSegment(seg);return e}
    if role=="client" {
        return runClient(ctx,cfg,uint32(iface.Index),tun,raw,emit,&connected)
    }
    return runServer(ctx,cfg,uint32(iface.Index),tun,raw,emit,&connected)
}
func logAuthenticOuter(role string,v realityfront.V4PublicOuterCounters,err error){
    if err!=nil{
        log.Printf("V4_PUBLIC_M2_OUTER_NOT_AVAILABLE role=%s error=%v",role,err)
        return
    }
    log.Printf("V4_PUBLIC_M2_OUTER role=%s real_first_copy=%d authenticated_ack=%d original_frozen_retransmitted=%d driver_uncertain=%d quota_or_capacity_blocked=%d retired_total=%d max_retransmits=2",
        role,v.FirstKernelCopied,v.AuthenticatedAckRetired,
        v.OriginalFrozenRepaired,v.DriverUncertain,
        v.BudgetOrCapacityBlocked,v.RetiredTotal)
}
func runClient(ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,connected *bool)error{
    flow:=faketcp.ClientFlow{LocalIP:c.localIP.As4(),PeerIP:c.peerIP.As4(),
        LocalPort:c.localPort,PeerPort:c.peerPort}
    isn,err:=originalRandomISN()
    if err!=nil{return err}
    assoc,err:=faketcp.NewClientAssociation(flow,isn,time.Second,emit)
    if err!=nil{return err}
    defer assoc.Close()
    errs:=make(chan error,1)
    go func(){
        for {
            seg,_,readErr:=raw.ReadSegment()
            if readErr!=nil{
                select{case <-ctx.Done():return;default:}
                select{case errs<-readErr:default:}
                return
            }
            if !flow.MatchesInbound(seg){continue}
            if assoc.State()!=faketcp.ClientAssociationDetached{
                if e:=assoc.HandleSegment(seg,time.Now());e!=nil &&
                   !errors.Is(e,faketcp.ErrClientDetached){
                    select{case errs<-e:default:}
                }
            }
        }
    }()
    if err:=assoc.Start(time.Now());err!=nil{return err}
    dialCtx,cancel:=context.WithTimeout(ctx,20*time.Second)
    defer cancel()
    if err:=assoc.WaitEstablished(dialCtx);err!=nil{return err}
    var policy realityfront.AdmissionPolicy
    switch c.fecMode{
    case realityfront.FecV2Fixed:
        policy,err=realityfront.FixedPolicyForClient(1,4)
    case realityfront.FecV2Auto:
        policy,err=realityfront.PolicyForClientWithInitial(1,"auto",0,4,20)
    default:
        policy,err=realityfront.FixedPolicyForClient(1,0)
    }
    if err!=nil{return err}
    native,err:=realityfront.NewV4LinuxClientProduct(
        realityfront.V4LinuxClientProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,CleanupOwnedNetwork:tun.Close,
            FECMode:c.fecMode,FECProfile:c.fecProfile,
        })
    if err!=nil{return err}
    cfg:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{ServerName:c.serverName,RouteKey:c.routeKey,Timeout:15*time.Second},
        Username:c.username,Password:c.password,TunnelID:c.tunnel[:],
        ClientLimit:1180,DesiredLanes:1,LaneID:1,Policy:policy,
    }
    if _,err=native.ConnectAuthenticatedPeer(dialCtx,assoc,cfg);err!=nil{return err}
    *connected=true
    log.Printf("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client Rust_owner=active real_raw_tun=1")
    select{
    case <-ctx.Done():
    case err=<-errs:
    }
    counters,countErr:=native.OriginalOuterCounters()
    logAuthenticOuter("client",counters,countErr)
    if c.fecMode!=realityfront.FecV2Off {
        actual,e:=native.OriginalFECReadback()
        if e!=nil {log.Printf("V4_PUBLIC_FEC2_READBACK_ERROR role=client error=%v",e)}
        if e==nil {log.Printf("V4_PUBLIC_FEC2_READBACK role=client mode=%s requested=%d applied=%d profile=%d pending=%t",actual.Mode,actual.RequestedRevision,actual.AppliedRevision,actual.Profile,actual.Pending)}
    }
    closeErr:=native.Close()
    if closeErr==nil{log.Printf("V4_PUBLIC_NATIVE_STOP_DRAINED role=client")}
    if err!=nil{return errors.Join(err,closeErr)}
    return closeErr
}
func runServer(ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,connected *bool)error{
    certificate,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    epochs,err:=realityfront.NewV4EpochStore(16)
    if err!=nil{return err}
    product,err:=realityfront.NewV4LinuxServerProduct(
        realityfront.V4LinuxServerProductConfig{
            Epochs:epochs,NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,CleanupOwnedNetwork:tun.Close,
            FECMode:c.fecMode,FECProfile:c.fecProfile,
        })
    if err!=nil{return err}
    table,err:=faketcp.NewServerAssociationTable(32,emit)
    if err!=nil{return err}
    reply:=realityfront.ServerAdmissionConfig{
        TLS:realityfront.ServerConfig{ServerName:c.serverName,RouteKey:c.routeKey,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{certificate}},
            Timeout:15*time.Second},
        ExpectedUsername:c.username,ExpectedPassword:c.password,ServerLimit:1180,
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            if len(req.TunnelID)!=16 || string(req.TunnelID)!=string(c.tunnel[:]) ||
               req.DesiredLanes!=1||req.LaneID!=1{return realityfront.ErrAdmissionParams}
            return nil
        },
    }
    errs:=make(chan error,1)
    admitted:=make(chan struct{},1)
    go func(){
        for {
            seg,_,readErr:=raw.ReadSegment()
            if readErr!=nil{
                select{case <-ctx.Done():return;default:}
                select{case errs<-readErr:default:}
                return
            }
            if seg.DstPort!=c.localPort{continue}
            if faketcp.IsInitialSYN(seg){
                if *connected{continue}
                isn,e:=originalRandomISN()
                if e!=nil{select{case errs<-e:default:};return}
                assoc,e:=table.AddSYN(seg,isn,time.Second)
                if errors.Is(e,faketcp.ErrAssociationExists){continue}
                if e!=nil{select{case errs<-e:default:};return}
                synack,e:=assoc.SYNACKSegment()
                if e==nil{e=emit(synack)}
                if e!=nil{select{case errs<-e:default:};return}
                continue
            }
            assoc,ok:=table.GetSegment(seg)
            if !ok || assoc.State()==faketcp.ServerAssociationClosed{continue}
            if state,exists:=assoc.TransitionState();exists &&
               state==faketcp.TransitionDetached{
                // Only post-Detach ciphertext belongs to Rust. During
                // PREPARED the original TLS protected reply is still an
                // in-flight FakeTCP write: sender ACK/window updates MUST
                // continue. Skipping all non-nil transitions deadlocked the
                // server before it could publish the real Rust owner.
                continue
            }
            outcome,e:=assoc.HandleSegment(seg,time.Now())
            if e!=nil{
                if !errors.Is(e,faketcp.ErrHandshakeState){
                    select{case errs<-e:default:}
                }
                continue
            }
            if outcome.AckNeeded{if e=emit(assoc.ACKSegment(outcome.Ack));e!=nil{
                select{case errs<-e:default:};return
            }}
            if assoc.State()==faketcp.ServerAssociationEstablished{
                select{case admitted<-struct{}{}:
                    go func(){
                        _,e:=product.AcceptAuthenticatedPeer(ctx,assoc,reply)
                        if e!=nil{select{case errs<-e:default:{}}}
                        if e==nil{
                            *connected=true
                            log.Printf("V4_ORIGINAL_GO_SERVER_NATIVE_READY role=server Rust_owner=active real_raw_tun=1")
                        }
                    }()
                default:}
            }
        }
    }()
    select{case <-ctx.Done():case err=<-errs:}
    if *connected{
        counters,countErr:=product.OriginalOuterCounters()
        logAuthenticOuter("server",counters,countErr)
        if c.fecMode!=realityfront.FecV2Off {
            actual,e:=product.OriginalFECReadback()
            if e!=nil {log.Printf("V4_PUBLIC_FEC2_READBACK_ERROR role=server error=%v",e)}
            if e==nil {log.Printf("V4_PUBLIC_FEC2_READBACK role=server mode=%s requested=%d applied=%d profile=%d pending=%t",actual.Mode,actual.RequestedRevision,actual.AppliedRevision,actual.Profile,actual.Pending)}
        }
        closeErr:=product.Close()
        if closeErr==nil{log.Printf("V4_PUBLIC_NATIVE_STOP_DRAINED role=server")}
        if err!=nil{return errors.Join(err,closeErr)}
        return closeErr
    }
    return err
}
