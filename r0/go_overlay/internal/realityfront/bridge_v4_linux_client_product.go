//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

// Original-Go protected V4 CLIENT -> actual Rust role-bound generation with
// real M4 raw/TUN and joined continuous worker. The published legacy V3
// DialTunnelClient is deliberately untouched: it must never process V4
// ciphertext under a V3 owner. New FEC2/Game capability promotion requires
// separate actual native client parity/independent-lane owner integrations.
import (
    "context"
    "errors"
    "fmt"
    "log"
    "net"
    "net/netip"
    "os"
    "runtime"
    "sync"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4LinuxClientProductConfig struct {
    NetworkInterface string
    NetworkIfIndex uint32
    // Required only on Android: the real ConnectivityManager Network handle
    // and link MTU are supplied by the root App's cold controller. Zero is
    // never interpreted as the default/physical network on Bionic.
    AndroidPhysicalNetworkHandle uint64
    AndroidPhysicalMTU uint32
    // Android original M3 TUN UDP/53 only; normal/off, not Android system
    // Resolver/netd, CN physical split, or FakeIP. Default disabled for CLI.
    AndroidTunnelDNS bool
    // Explicit ordinary-App UDP53 physical 223.5.5.5 compatibility mode.
    AndroidPhysicalDNS bool
    AndroidPhysicalDNSUpstream netip.Addr // original Rust bound UDP53 destination
    // Cold Go-verified CN8503 snapshot only. No per-query Go callback.
    AndroidCN8503Raw []byte
    Tun *os.File
    TunName string
    // Only original Go authenticated AUTO /32 client mode uses one shared
    // Rust physical TUN reader; future same-process generation A+B can't
    // race destructive kernel TUN reads. Normal manual mode unchanged.
    SharedTun *V4LinuxSharedTun
    CleanupOwnedNetwork func()error
    // Optional original OS owner callback, only after authentication and before TUN starts.
    ConfigureTunnelMTU func(peerMSS,clientLimit,serverLimit uint16)error
    ConfigureLeaseIPv4 func(lease string)error // protected reply, pre-native business
    FECMode FecV2Mode
    FECProfile FecV2Profile
    DisableOuterRepair bool
    StartupPaddingMode uint8 // client protected V2: Normal kind1 or FEC kind2 source off/tls/flows
    OuterIPMTU int // cold original Go complete IPv4 budget
    // Zero interval/dead keeps original product defaults 15s/90s.
    // Dormant 0 means no automatic sleep; nonzero policy must have real
    // authenticated FIN and independently proven peer idle before use.
    HealthKeepaliveSeconds uint32
    HealthDeadAfterSeconds uint32
    HealthIdleDormantSeconds uint32
}
type V4LinuxClientProduct struct {
    mu sync.Mutex
    cfg V4LinuxClientProductConfig
    owner *v4EmbeddedNativeBridge
    session *V4ClientSession
    association *faketcp.ClientAssociation
    fec *v4ProductFecMonitor
    stopped bool
}
func NewV4LinuxClientProduct(cfg V4LinuxClientProductConfig)(*V4LinuxClientProduct,error){
    if cfg.Tun==nil||cfg.CleanupOwnedNetwork==nil||cfg.NetworkIfIndex==0||
       cfg.NetworkInterface==""||len(cfg.TunName)==0||len(cfg.TunName)>15{
        return nil,ErrAdmissionParams
    }
    iface,err:=net.InterfaceByName(cfg.NetworkInterface)
    if err!=nil||iface==nil||uint32(iface.Index)!=cfg.NetworkIfIndex{
        return nil,ErrAdmissionParams
    }
    if runtime.GOOS=="android" && (cfg.AndroidPhysicalNetworkHandle==0||
        cfg.AndroidPhysicalMTU<68||cfg.AndroidPhysicalMTU>65535||
        uint32(iface.MTU)!=cfg.AndroidPhysicalMTU){
        return nil,ErrAdmissionParams
    }
    if _,err:=cfg.Tun.Stat();err!=nil{return nil,errors.Join(ErrAdmissionParams,err)}
    if cfg.FECMode!=""&&cfg.FECMode!=FecV2Off&&
        !v4ProductFecEnabled(cfg.FECMode){return nil,ErrAdmissionUnsupported}
    if cfg.FECMode==FecV2Fixed&&!cfg.FECProfile.Valid(){return nil,ErrAdmissionParams}
    if cfg.StartupPaddingMode>2||
       (cfg.StartupPaddingMode!=0&&(cfg.OuterIPMTU<576||cfg.OuterIPMTU>1500)){
        return nil,ErrAdmissionParams
    }
    // Go's Android target also satisfies Linux build constraints.
    // Native original M4 now owns TLS-selected Normal padding on both.
    if runtime.GOOS!="android"&&(cfg.AndroidTunnelDNS||cfg.AndroidPhysicalDNS||len(cfg.AndroidCN8503Raw)>0){
        return nil,ErrAdmissionUnsupported
    }
    return &V4LinuxClientProduct{cfg:cfg},nil
}
// A40 stages are emitted by real original client transitions after protected
// TLS admission; not synthetic M4/lease evidence.
func originalAndroidPostauth(stage string){
    if runtime.GOOS=="android"{
        log.Printf("V4_PUBLIC_ANDROID_POSTAUTH role=client class=%s",stage)
    }
}
// ConnectAuthenticatedPeer is the real TLS client public product half:
// original Go FakeTCP SYN/SYNACK must be established and receive handling
// active; only the verified V4 protected reply can install native keys.
// Exact original Go Detach, not a guessed TCP seq, grants the Rust generation.
// No test-only sender, cold fixture, or legacy V3 data plane is involved.
func (p *V4LinuxClientProduct) ConnectAuthenticatedPeer(
    ctx context.Context,assoc *faketcp.ClientAssociation,cfg ClientAdmissionConfig,
)(*V4ClientSession,error){
    if p==nil||assoc==nil{return nil,ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner!=nil||p.session!=nil||p.stopped{return nil,ErrAdmissionUnsupported}
    // Android Normal default, explicit Fixed/Auto on same authenticated
    // original Rust feature7 FEC2 M4. FEC2 never uses Normal-only pad.
    if runtime.GOOS=="android" &&
       (!p.cfg.DisableOuterRepair||p.cfg.SharedTun!=nil||
        !cfg.AutoLease||
        (v4ProductFecEnabled(p.cfg.FECMode)&&p.cfg.StartupPaddingMode!=0)){
        return nil,ErrAdmissionUnsupported
    }
    conn:=assoc.BootstrapConn()
    if conn==nil{return nil,ErrAdmissionParams}
    // One TLS exporter binds the requested FEC mode to the same
    // original-Go V4 Rust owner, never a legacy V3 separate FEC stream.
    mode:=p.cfg.FECMode
    if mode==""{mode=FecV2Off}
    wireMode:=FECOff
    if mode==FecV2Fixed{wireMode=FECFixed}
    if mode==FecV2Auto{wireMode=FECAuto}
    if cfg.Policy.Transport!=TransportNormal||
       cfg.Policy.FECMode!=wireMode||cfg.DesiredLanes!=1{
        return nil,ErrAdmissionUnsupported
    }
    normalProfile:=uint8(0)
    if mode==FecV2Fixed{normalProfile=uint8(p.cfg.FECProfile)+1}
    session,err:=EstablishClientV4(ctx,conn,cfg,V4ClientOptions{
        DataPlaneReady:true,fec2Product:v4ProductFecEnabled(mode),
        NormalFec:normalProfile,
        StartupPadding:p.cfg.StartupPaddingMode,
    })
    if err!=nil{return nil,err}
    cold,err:=session.ColdSnapshot()
    if err!=nil||cold.ServerSide(){
        originalAndroidPostauth("COLD_FAILED")
        if err!=nil{return nil,err}
        return nil,ErrAdmissionParams
    }
    originalAndroidPostauth("COLD_OK")
    handoff,err:=assoc.Detach()
    if err!=nil{
        originalAndroidPostauth("DETACH_FAILED")
        return nil,err
    }
    originalAndroidPostauth("DETACH_OK")
    bridge:=&v4EmbeddedNativeBridge{}
    if err=bridge.prepareAuthenticatedClient(session,handoff,assoc.Flow());err!=nil{
        switch V4OriginalNativeM4FailureStage(err){
        case "original_native_prepare":originalAndroidPostauth("NATIVE_PREPARE_FAILED")
        case "original_native_commit":originalAndroidPostauth("NATIVE_COMMIT_FAILED")
        default:originalAndroidPostauth("NATIVE_OTHER_FAILED")
        }
        return nil,fmt.Errorf("V4 genuine Go client TLS/native owner: %w",err)
    }
    originalAndroidPostauth("NATIVE_COMMIT_OK")
    p.owner=bridge
    p.session=session
    p.association=assoc
    // Never let Rust begin TUN business before the original authenticated
    // server-selected per-device IPv4 address has been installed/read back.
    if cfg.AutoLease {
        lease,leaseErr:=session.AuthenticatedLeaseIPv4()
        if leaseErr!=nil||lease==""||p.cfg.ConfigureLeaseIPv4==nil {
            originalAndroidPostauth("LEASE_FIELD_FAILED")
            return nil,errors.Join(ErrAdmissionParams,leaseErr,p.closeLocked())
        }
        originalAndroidPostauth("LEASE_FIELD_OK")
        if leaseErr=p.cfg.ConfigureLeaseIPv4(lease);leaseErr!=nil {
            originalAndroidPostauth("LEASE_OS_FAILED")
            return nil,errors.Join(leaseErr,p.closeLocked())
        }
        originalAndroidPostauth("LEASE_OS_OK")
        if runtime.GOOS=="android"{
            // The real Go-authenticated installed /32 must also restrict
            // the native ARM64 TUN reverse-destination, even without the
            // Linux SharedTun process-wide reader.
            if leaseErr=bridge.bindAuthenticatedClientIPv4(lease);leaseErr!=nil{
                originalAndroidPostauth("NATIVE_IP_BIND_FAILED")
                return nil,errors.Join(leaseErr,p.closeLocked())
            }
            originalAndroidPostauth("NATIVE_IP_BOUND")
        }
        if p.cfg.SharedTun!=nil {
            // Original protected lease has ALREADY been installed and
            // verified by the actual OS before the client may bind the
            // process-wide default Rust M1 ingress. A forged mutable
            // admission result or pre-TLS configuration is never authority.
            if runtime.GOOS!="android"{
                if leaseErr=bridge.bindAuthenticatedClientIPv4(lease);leaseErr!=nil{
                    return nil,errors.Join(leaseErr,p.closeLocked())
                }
            }
            if leaseErr=bridge.bindAuthenticatedSharedTun(p.cfg.SharedTun);leaseErr!=nil {
                return nil,errors.Join(leaseErr,p.closeLocked())
            }
        }
    }else if p.cfg.SharedTun!=nil {
        return nil,errors.Join(ErrAdmissionParams,p.closeLocked())
    }
    if p.cfg.ConfigureTunnelMTU!=nil {
        clientLimit,serverLimit:=cold.RecordLimits()
        if err=p.cfg.ConfigureTunnelMTU(handoff.Peer.MSS,clientLimit,serverLimit);err!=nil{
            originalAndroidPostauth("MTU_FAILED")
            return nil,errors.Join(err,p.closeLocked())
        }
    }
    // Android cannot inherit Linux's implicit physical interface binding.
    // Fail closed if the OS Network handle/MTU cannot be pinned to this
    // specific Go-authenticated Rust generation before either FD is opened.
    err=v4BindPlatformUnderlay(bridge,p.cfg)
    if err!=nil{originalAndroidPostauth("UNDERLAY_FAILED")
    }else{originalAndroidPostauth("UNDERLAY_OK")}
    if err==nil{
        err=bridge.attachRawRxOnInterface(p.cfg.NetworkInterface,p.cfg.NetworkIfIndex)
        if err!=nil{originalAndroidPostauth("RAW_FAILED")
        }else{originalAndroidPostauth("RAW_ATTACHED")}
    }
    if err==nil{
        err=bridge.attachKernelTun(p.cfg.Tun.Fd(),p.cfg.TunName)
        if err!=nil{originalAndroidPostauth("TUN_FAILED")
        }else{originalAndroidPostauth("TUN_ATTACHED")}
    }
    if err==nil&&runtime.GOOS=="android"&&
       (len(p.cfg.AndroidCN8503Raw)>0||p.cfg.AndroidPhysicalDNS){
        upstream:=p.cfg.AndroidPhysicalDNSUpstream
        if !upstream.IsValid(){upstream=netip.MustParseAddr("223.5.5.5")}
        p.cfg.AndroidPhysicalDNSUpstream=upstream
        err=bridge.setAndroidPhysicalDNSUpstream(upstream)
        if err!=nil{originalAndroidPostauth("PHYSICAL_DNS_FAILED")}
    }
    if err==nil&&runtime.GOOS=="android"&&len(p.cfg.AndroidCN8503Raw)>0{
        err=bridge.enableAndroidCNDNSSplit(p.cfg.AndroidCN8503Raw)
        if err!=nil{
            originalAndroidPostauth("CN_DNS_SPLIT_FAILED")
        }else{
            originalAndroidPostauth("CN_DNS_SPLIT_ENABLED")
            log.Printf("V4_PUBLIC_ANDROID_CN_DNS_SPLIT_EFFECTIVE role=client rules=8503 cn=%s noncn=1.1.1.1 system_resolver=NOT_CAPTURED",p.cfg.AndroidPhysicalDNSUpstream.String())
        }
    }else if err==nil&&runtime.GOOS=="android"&&p.cfg.AndroidPhysicalDNS{
        // Separate explicit all-App TUN UDP53 physical mode, not CN split
        // and never an Android system Resolver/netd takeover.
        err=bridge.enableAndroidPhysicalDNS()
        if err!=nil{
            originalAndroidPostauth("PHYSICAL_DNS_FAILED")
        }else{
            originalAndroidPostauth("PHYSICAL_DNS_ENABLED")
            log.Printf("V4_PUBLIC_ANDROID_PHYSICAL_DNS_EFFECTIVE role=client cold=1 app_tun_udp53=1 upstream=%s cn_split=NOT_ACTIVE system_resolver=NOT_CAPTURED",p.cfg.AndroidPhysicalDNSUpstream.String())
        }
    }else if err==nil&&runtime.GOOS=="android"&&p.cfg.AndroidTunnelDNS{
        // Real original-Go cold grant after true TLS/lease/RAW/TUN binding.
        // The original Rust worker, M3, inverse map and owned Stop already
        // exist; neither Go nor Java processes any DNS DATA packet.
        err=bridge.enableAndroidTunnelDNS()
        if err!=nil{
            originalAndroidPostauth("TUNNEL_DNS_FAILED")
        }else{
            originalAndroidPostauth("TUNNEL_DNS_ENABLED")
            log.Print("V4_PUBLIC_ANDROID_TUNNEL_DNS_EFFECTIVE role=client enabled=1 original_m3=1 system_resolver=NOT_CAPTURED cn_split=NOT_ACTIVE")
        }
    }
    if err==nil{
        p.fec,err=v4ConfigureProductFec(bridge,mode,p.cfg.FECProfile,cold)
    }
    if err==nil&&runtime.GOOS!="android"{
        err=bridge.configureOriginalOuterRepair(!p.cfg.DisableOuterRepair)
    }
    if err==nil{
        keepalive,dead:=p.cfg.HealthKeepaliveSeconds,p.cfg.HealthDeadAfterSeconds
        if keepalive==0{keepalive=15}
        if dead==0{dead=90}
        err=bridge.configureOriginalNativeHealth(keepalive,dead,p.cfg.HealthIdleDormantSeconds)
        if err!=nil{originalAndroidPostauth("HEALTH_FAILED")}
    }
    if err==nil&&mode==FecV2Auto{err=bridge.enableOriginalLowRateAuto()}
    if err==nil&&p.cfg.OuterIPMTU!=0&&
        (runtime.GOOS!="android"||mode==FecV2Off){
        // Fixed's original FEC2 source budget is independent of
        // Android Normal-only startup padding; Fixed requires off.
        err=bridge.configureNormalStartupPadding(cold.StartupPaddingMode(),p.cfg.OuterIPMTU)
    }
    // Source-locked Android feature3/off does not advertise the unported
    // original mature firstsend M2 receipt/outer repair capability.
    // The original TLS/AEAD/replay and canonical encrypted Health stay live.
    if err==nil&&runtime.GOOS!="android"{
        err=bridge.armOriginalPublicM2Feedback(0)
    }
    if err==nil{
        err=bridge.startRustOwnerLoop(p.cfg.NetworkIfIndex)
        if err!=nil{originalAndroidPostauth("M4_START_FAILED")
        }else{originalAndroidPostauth("M4_STARTED")}
    }
    if err!=nil{
        shutdown:=p.closeLocked()
        return nil,errors.Join(
            fmt.Errorf("V4 original Go client M4 raw/TUN worker start: %w",err),
            shutdown,
        )
    }
    // Fixed uses only native Quality. Android Auto alone starts the
    // original 2Hz Go policy readback, never a per-DATA Go callback.
    if p.fec!=nil&&(runtime.GOOS!="android"||mode==FecV2Auto){
        p.fec.start(bridge)
    }
    return session,nil
}
// Only numeric true original M2 counters, once before Stop; never changes
// TLS, ACK, FEC policy, mode revision or owner state.
func (p *V4LinuxClientProduct) OriginalNormalStartupPaddingCounters()(string,uint64,uint64,error){
    if p==nil{return "",0,0,ErrAdmissionParams}
    p.mu.Lock();defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return "",0,0,ErrAdmissionUnsupported}
    return p.owner.normalStartupPaddingCounters()
}
func (p *V4LinuxClientProduct) OriginalFecM2Proof()(V4PublicFecM2Proof,error){
    if p==nil{return V4PublicFecM2Proof{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecM2Proof{},ErrAdmissionUnsupported}
    return v4ReadOriginalFecM2Proof(p.owner)
}
// Authentic original TUN intake counters only while this TLS FEC owner lives.
// Same product-native owner, solely numeric evidence before Stop.
func (p *V4LinuxClientProduct) OriginalFecM1Stage()(V4PublicFecM1Stage,error){
    if p==nil{return V4PublicFecM1Stage{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecM1Stage{},ErrAdmissionUnsupported}
    return v4ReadOriginalFecM1Stage(p.owner)
}
func (p *V4LinuxClientProduct) OriginalFecM1Ingress()(V4PublicFecM1Ingress,error){
    if p==nil{return V4PublicFecM1Ingress{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecM1Ingress{},ErrAdmissionUnsupported}
    return v4ReadOriginalFecM1Ingress(p.owner)
}
func (p *V4LinuxClientProduct) OriginalFecRxIpClass()(V4PublicFecRxIpClass,error){
    if p==nil{return V4PublicFecRxIpClass{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecRxIpClass{},ErrAdmissionUnsupported}
    return v4ReadOriginalFecRxIpClass(p.owner)
}
func (p *V4LinuxClientProduct) OriginalFecRxProof()(V4PublicFecRxProof,error){
    if p==nil{return V4PublicFecRxProof{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecRxProof{},ErrAdmissionUnsupported}
    return v4ReadOriginalFecRxProof(p.owner)
}
func (p *V4LinuxClientProduct) OriginalFECReadback()(V4PublicFecReadback,error){
    if p==nil{return V4PublicFecReadback{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.fec==nil||p.owner==nil||p.stopped{return V4PublicFecReadback{},ErrAdmissionUnsupported}
    return p.fec.readback(p.owner)
}
// Real original Go TLS owner M2 wire counters before Stop. No GUI/CLI
// operator can forge these numbers; every metric comes from original Rust.
func (p *V4LinuxClientProduct) OriginalFecTxFailures()(V4PublicFecTxFailures,error){
    if p==nil{return V4PublicFecTxFailures{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicFecTxFailures{},ErrAdmissionUnsupported}
    return p.owner.originalPublicFecTxFailures()
}
func (p *V4LinuxClientProduct) OriginalFecTxSnapshot()(V4PublicFecTxSnapshot,error){
    if p==nil{return V4PublicFecTxSnapshot{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicFecTxSnapshot{},ErrAdmissionUnsupported}
    return p.owner.originalPublicFecTxSnapshot()
}
// Only the original native RX owner's delivered/authenticated reverse
// packets can promote a replacement client generation's shared-TUN route.
// This is NOT local TLS Ready, packet TX, Go DATA or a synthetic receipt.
func (p *V4LinuxClientProduct) PromoteNormalAfterAuthenticatedPeerRx()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return ErrAdmissionUnsupported}
    return p.owner.promoteNormalSharedTunAfterAuthenticatedRx()
}
func (p *V4LinuxClientProduct) OriginalLoopPulse()(V4PublicLoopPulse,error){
    if p==nil{return V4PublicLoopPulse{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicLoopPulse{},ErrAdmissionUnsupported}
    return p.owner.originalPublicLoopPulse()
}
func (p *V4LinuxClientProduct) OriginalWorkerCPU()(V4PublicWorkerCPU,error){
    if p==nil{return V4PublicWorkerCPU{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicWorkerCPU{},ErrAdmissionUnsupported}
    return p.owner.originalPublicWorkerCPU()
}
func (p *V4LinuxClientProduct) OriginalOuterCounters()(V4PublicOuterCounters,error){
    if p==nil{return V4PublicOuterCounters{},ErrAdmissionParams}
    p.mu.Lock()
    defer p.mu.Unlock()
    if p.owner==nil||p.stopped{return V4PublicOuterCounters{},ErrAdmissionUnsupported}
    return p.owner.originalPublicOuterCounters()
}
func (p *V4LinuxClientProduct) Close()error{
    if p==nil{return ErrAdmissionParams}
    p.mu.Lock()
    worker:=p.fec
    p.mu.Unlock()
    if worker!=nil{worker.stop()}
    p.mu.Lock()
    defer p.mu.Unlock()
    return p.closeLocked()
}
func (p *V4LinuxClientProduct) closeLocked()error{
    if p.stopped{return nil}
    if p.owner==nil||p.session==nil{return ErrAdmissionUnsupported}
    _,err:=V4StopThenCleanupNetwork(p.owner,p.cfg.CleanupOwnedNetwork)
    if err!=nil{return err}
    if p.association!=nil{p.association.Close()}
    p.stopped=true
    return nil
}
