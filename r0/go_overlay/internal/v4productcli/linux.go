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
    "io"
    "log"
    "net"
    "net/netip"
    "os"
    "os/exec"
    "os/signal"
    "strconv"
    "strings"
    "sync/atomic"
    "syscall"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

const tunSetIFF=0x400454ca

const maxPrivateArgBytes = 4096

// Refuse symlinks, world/group-readable files, nonregular files and oversized
// secrets. Kernel O_NOFOLLOW and f.Stat apply to the SAME opened descriptor;
// caller never logs secret bytes or publishes their contents in argv.
func readPrivateArgFile(path string)(string,error){
    if path=="" {return "",fmt.Errorf("missing secret path")}
    fd,err:=syscall.Open(path,syscall.O_RDONLY|syscall.O_CLOEXEC|syscall.O_NOFOLLOW,0)
    if err!=nil{return "",err}
    f:=os.NewFile(uintptr(fd),"private-credential")
    defer f.Close()
    st,err:=f.Stat()
    if err!=nil{return "",err}
    if !st.Mode().IsRegular()||st.Mode().Perm()&0077!=0{
        return "",fmt.Errorf("secret must be a regular owner-only file")
    }
    b,err:=io.ReadAll(io.LimitReader(f,maxPrivateArgBytes+1))
    if err!=nil{return "",err}
    if len(b)==0||len(b)>maxPrivateArgBytes{
        return "",fmt.Errorf("secret length invalid")
    }
    value:=strings.TrimSuffix(strings.TrimSuffix(string(b),"\n"),"\r")
    if value==""||strings.IndexByte(value,0)>=0{
        return "",fmt.Errorf("secret contents invalid")
    }
    return value,nil
}


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
    gameFecEnabled bool
    gameFecProfile uint8
    game4CopyStagger bool
    outerMTU int
    disableOuterRepair bool
    recordLimit uint16
    innerMTU int
    tunFqMaxrateMbps int
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
    pass:=flags.String("password","","original protected admission password; prefer --password-file on shared devices")
    passFile:=flags.String("password-file","","mode-0600 regular secret file, no symlinks")
    routeFile:=flags.String("route-key-hex-file","","mode-0600 route key hex file, no symlinks")
    tunnel:=flags.String("tunnel-id","","original logical 16B hex tunnel id")
    mode:=flags.String("mode","normal","V4 normal, fec-fixed, fec-auto, game2, game4")
    profile:=flags.Uint("fec-profile",1,"FEC2 profile 0..6 for normal fixed; auto uses strong startup")
    gameFec:=flags.String("game-fec","off","Game2/4 inner fixed FEC: off or fixed0..fixed6; BOTH authenticated endpoints must match; no Game Auto")
    game4Copy:=flags.String("game4-copy-schedule","","Game4 default stagger-4-20-60, explicit immediate rollback; Game2 unaffected; usable with fixed6")
    outerRepair:=flags.String("outer-repair","on","outer DATA retransmission on|off; FEC parity and actual receipt feedback remain enabled")
    outerMTU:=flags.Int("outer-mtu",1500,"outer IPv4 packet MTU; inner TUN MTU is derived automatically and clamped to device/peer limits")
    tunFqRate:=flags.Int("tun-fq-maxrate-mbps",600,"owned Linux TUN per-flow fq maxrate Mbps: default 600 in all supported modes; explicit 0 disables")
    if err:=flags.Parse(args);err!=nil{return c,err}
    if *passFile!="" {
        if *pass!="" {return c,fmt.Errorf("password and password-file are mutually exclusive")}
        value,e:=readPrivateArgFile(*passFile)
        if e!=nil{return c,fmt.Errorf("invalid password-file: %w",e)}
        *pass=value
    }
    if *routeFile!="" {
        if *route!="" {return c,fmt.Errorf("route-key-hex and route-key-hex-file are mutually exclusive")}
        value,e:=readPrivateArgFile(*routeFile)
        if e!=nil{return c,fmt.Errorf("invalid route-key-hex-file: %w",e)}
        *route=value
    }
    switch *mode{
    case "normal":c.fecMode=realityfront.FecV2Off
    case "fec-fixed":c.fecMode=realityfront.FecV2Fixed
    case "fec-auto":c.fecMode=realityfront.FecV2Auto
    case "game2":c.gameLanes=2;c.fecMode=realityfront.FecV2Off
    case "game4":c.gameLanes=4;c.fecMode=realityfront.FecV2Off
    default:return c,fmt.Errorf("V4 mode %q not installed in native public owner",*mode)
    }
    if *profile>6{return c,fmt.Errorf("fec-profile must be 0..6")}
    if *gameFec!="off"{
        if c.gameLanes==0||len(*gameFec)!=6||!strings.HasPrefix(*gameFec,"fixed")||
           (*gameFec)[5]<'0'||(*gameFec)[5]>'6'{
            return c,fmt.Errorf("game-fec must be off or fixed0..fixed6 on game2/game4")
        }
        c.gameFecEnabled=true
        c.gameFecProfile=uint8((*gameFec)[5]-'0')
    }
    if *game4Copy=="" {
        if c.gameLanes==4 {*game4Copy="stagger-4-20-60"
        } else {*game4Copy="immediate"}
    }
    switch *game4Copy{
    case "immediate":
    case "stagger-4-20-60":
        if c.gameLanes!=4{
            return c,fmt.Errorf("game4-copy-schedule stagger requires game4")
        }
        c.game4CopyStagger=true
    default:return c,fmt.Errorf("game4-copy-schedule must be immediate or stagger-4-20-60")
    }
    if *outerMTU<576||*outerMTU>9000{return c,fmt.Errorf("outer-mtu must be 576..9000")}
    // User authorized product-owned fq600 for ALL Linux public modes:
    // Normal/off, FEC Fixed/Auto, Game2/Game4. It is applied only after
    // creating our ephemeral TUN; explicit0 remains a safe rollback.
    if *tunFqRate!=0 && *tunFqRate!=600 {
        return c,fmt.Errorf("tun-fq-maxrate-mbps must be 0 or 600")
    }
    c.tunFqMaxrateMbps=*tunFqRate
    switch *outerRepair{
    case "on":c.disableOuterRepair=false
    case "off":c.disableOuterRepair=true
    default:return c,fmt.Errorf("outer-repair must be on or off")
    }
    c.outerMTU=*outerMTU
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
// Only the newly-owned ephemeral TUN is modified: never host/global sysctls
// or arbitrary application TCP sockets. If tc/kernel fq is unavailable,
// fail closed instead of claiming protected startup traffic.
func setOwnedTunFq(name string,rateMbps int)error{
    if rateMbps==0{return nil}
    if rateMbps!=600{return fmt.Errorf("unsupported owned TUN fq rate")}
    // The default kernel fq flow_limit=100 dropped two real warmup UDP
    // frames at 370Mbps despite a 500Mbps outer line (flows_plimit=2).
    // 256 near-MTU packets are at most ~384KiB per flow; global fq
    // limit=10000 remains unchanged and bounds aggregate queue memory.
    cmd:=exec.Command("tc","qdisc","replace","dev",name,"root","fq",
        "maxrate",strconv.Itoa(rateMbps)+"mbit","flow_limit","256")
    if b,err:=cmd.CombinedOutput();err!=nil{
        return fmt.Errorf("owned TUN fq setup: %w %s",err,b)
    }
    b,err:=exec.Command("tc","-d","qdisc","show","dev",name).CombinedOutput()
    if err!=nil{return fmt.Errorf("owned TUN fq readback: %w %s",err,b)}
    for _,line:=range strings.Split(string(b),"\n"){
        if strings.HasPrefix(line,"qdisc fq ") &&
            strings.Contains(line," root ") &&
            strings.Contains(line," maxrate 600Mbit") &&
            strings.Contains(line," flow_limit 256"){
            return nil
        }
    }
    return fmt.Errorf("owned TUN fq maxrate readback mismatch on %s",name)
}
type ownedTun struct{
    f *os.File
    name string
    cleaned bool
    mtu int
}
// Original kernel-owned /dev/net/tun FD, never a synthetic traffic adapter.
func openTun(name,cidr string,mtu int)(*ownedTun,error){
    fd,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{return nil,err}
    var ifr [40]byte
    copy(ifr[:16],[]byte(name))
    binary.NativeEndian.PutUint16(ifr[16:18],0x1001) // IFF_TUN | IFF_NO_PI
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,fd.Fd(),tunSetIFF,
        uintptr(unsafe.Pointer(&ifr[0])))
    if errno!=0{_ = fd.Close();return nil,errno}
    device:=&ownedTun{f:fd,name:name,mtu:mtu}
    // This public TUN is IPv4-only. At MTU>=1280 Linux would otherwise create
    // IPv6 link-local/RS traffic, which the IPv4 driver correctly rejects.
    // Set only our newly-owned device, before bringing it up; no host sysctl.
    err=os.WriteFile("/proc/sys/net/ipv6/conf/"+name+"/disable_ipv6",[]byte("1\n"),0)
    if err!=nil&&!errors.Is(err,os.ErrNotExist){_ = device.Close();return nil,err}
    if err=runIP("addr","add",cidr,"dev",name);err==nil{
        err=runIP("link","set","dev",name,"mtu",strconv.Itoa(mtu),"up")
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
    // Product SYN MSS and initial record offer are computed from the same
    // real cold outer/interface envelope. No inherited 1360/1280 ceiling.
    publicMSS:=min(cfg.outerMTU,iface.MTU)-40
    if publicMSS<536||publicMSS>8960{return fmt.Errorf("unsupported public IPv4 MSS %d",publicMSS)}
    if err=faketcp.SetPublicV4AdvertisedMSS(uint16(publicMSS));err!=nil{return err}
    cfg.recordLimit,cfg.innerMTU,err=deriveMTUBudget(cfg.outerMTU,iface.MTU,
        uint16(publicMSS),0,cfg.fecMode,cfg.gameLanes!=0)
    if err!=nil{return err}
    cfg.innerMTU,err=gameFecBudget(cfg,cfg.innerMTU)
    if err!=nil{return err}
    log.Printf("V4_PUBLIC_MTU_PREPARE role=%s mtu_budget_version=3 outer_config=%d interface=%d advertised_mss=%d record_offer=%d tun_planned=%d",cfg.role,cfg.outerMTU,iface.MTU,publicMSS,cfg.recordLimit,cfg.innerMTU)
    tun,err:=openTun(cfg.tunName,cfg.tunCIDR,cfg.innerMTU)
    if err!=nil{return err}
    // This fallback is ONLY used if no authenticated Rust owner was started.
    // An active owner's Close performs Stop->release->network cleanup instead.
    connected:=false
    defer func(){if !connected {_ = tun.Close()}}()
    if err=setOwnedTunFq(tun.name,cfg.tunFqMaxrateMbps);err!=nil{return err}
    if cfg.tunFqMaxrateMbps!=0 {
        log.Printf("V4_PUBLIC_TUN_FQ role=%s interface=%s maxrate_mbps=600 flow_limit_packets=256 readback=kernel_fq_600Mbit",cfg.role,tun.name)
    } else {
        log.Printf("V4_PUBLIC_TUN_FQ role=%s interface=%s maxrate_mbps=0 readback=kernel_default",cfg.role,tun.name)
    }
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
// Opt-in native V3 diagnostic, OFF by default. Samples only every 250ms;
 // no packet timestamps, packet payloads, heap per-record work or control ACK
 // changes. A bounded series can distinguish TUN-M4 progress from raw-M4 RX
 // and native worker CPU across netem blackhole/restore transitions.
func startV3ProductTimeline(ctx context.Context,role string,
    pulse func()(realityfront.V4PublicLoopPulse,error),
    outer func()(realityfront.V4PublicOuterCounters,error)){
    if os.Getenv("WBD_V3_TIMELINE")!="1"{return}
    go func(){
        ticker:=time.NewTicker(250*time.Millisecond)
        defer ticker.Stop()
        for{
            select{
            case <-ctx.Done(): return
            case <-ticker.C:
                s,e:=pulse()
                if e!=nil{continue}
                o,e:=outer()
                if e!=nil{continue}
                log.Printf("V4_PUBLIC_TIMELINE role=%s unix_ns=%d rx_records=%d tx_records=%d rx_err=%d tx_err=%d rust_rx_cpu_ns=%d rust_tx_cpu_ns=%d first_wire_bytes=%d repair_wire_bytes=%d",
                    role,time.Now().UnixNano(),s.RxRecords,s.TxRecords,s.RxErrors,s.TxErrors,
                    s.RxThreadCPUns,s.TxThreadCPUns,o.FirstWireBytes,o.RepairAcceptedWireBytes)
            }
        }
    }()
}
func logAuthenticOuter(role string,v realityfront.V4PublicOuterCounters,err error){
    if err!=nil{
        log.Printf("V4_PUBLIC_M2_OUTER_NOT_AVAILABLE role=%s error=%v",role,err)
        return
    }
    log.Printf("V4_PUBLIC_M2_OUTER role=%s policy=outer-opportunistic-v3 loss_trigger=authenticated_mature_gap data_pto=false shadow_sampling_numerator=1 shadow_sampling_denominator=2 admission_pps=32768 repair_pps=8192 byte_credit_pct=9 byte_cap_pct=10 repair_enabled=%d first_wire_bytes=%d repair_accepted_wire_bytes=%d repair_uncertain_wire_bytes=%d real_first_copy=%d authenticated_ack=%d original_frozen_retransmitted=%d driver_uncertain=%d quota_or_capacity_blocked=%d retired_total=%d repair_attempt_limit=%d shadow_limit=%d retain_cap_us=%d candidate_first=%d candidate_retry=%d acked0=%d acked1=%d acked2=%d expired0=%d expired1=%d expired2=%d repair_accepted_retired=%d repair_uncertain_retired=%d repair_abandoned_retired=%d max_queue_age_us=%d late_positive_expired=%d timing_samples=%d srtt_us=%d rttvar_us=%d recent_rtt_us=%d reorder_us=%d pto_us=%d cache_us=%d shadow_outstanding=%d blocked_fresh_global=%d blocked_fresh_shadow=%d blocked_grant=%d blocked_burst=%d blocked_quota=%d blocked_capacity=%d blocked_stale=%d blocked_local_other=%d blocked_global_other=%d blocked_invariant=%d",
        role,func()int{if v.OuterRepairEnabled{return 1};return 0}(),v.FirstWireBytes,v.RepairAcceptedWireBytes,v.RepairUncertainWireBytes,
        v.FirstKernelCopied,v.AuthenticatedAckRetired,
        v.OriginalFrozenRepaired,v.DriverUncertain,
        v.BudgetOrCapacityBlocked,v.RetiredTotal,
        v.RepairAttemptLimit,v.ShadowLimit,v.RetainCapus,
        v.CandidateFirst,v.CandidateRetry,
        v.AckedAttempt0,v.AckedAttempt1,v.AckedAttempt2,
        v.ExpiredAttempt0,v.ExpiredAttempt1,v.ExpiredAttempt2,
        v.RepairAcceptedRetired,v.RepairUncertainRetired,
        v.RepairAbandonedRetired,v.MaxQueueAgeus,
        v.LatePositiveExpired,v.TimingSamples,v.SRTTus,v.RTTVarus,
        v.RecentRTTus,v.Reorderus,v.PTOus,v.Cacheus,v.ShadowOutstanding,
        v.BlockedFreshGlobal,v.BlockedFreshShadow,v.BlockedGrant,
        v.BlockedBurst,v.BlockedQuota,v.BlockedCapacity,v.BlockedStale,
        v.BlockedLocalOther,v.BlockedGlobalOther,v.BlockedInvariant)
}
func logAuthenticFecTx(role string,v realityfront.V4PublicFecTxSnapshot,err error){
    if err!=nil{
        log.Printf("V4_PUBLIC_FEC2_TX_NOT_AVAILABLE role=%s error=%v",role,err)
        return
    }
    log.Printf("V4_PUBLIC_FEC2_TX role=%s accepted=%d notready=%d full=%d partial=%d k1=%d k2_4=%d k5_12=%d k13_16=%d rplanned=%d rsent=%d expired=%d pressure_jobs=%d pressure_sources=%d unknown_capacity=%d",
        role,v.Accepted,v.SourceNotReady,v.Full,v.Partial,v.K1,v.K2To4,
        v.K5To12,v.K13To16,v.RPlanned,v.RSent,v.ExpiredJobs,v.PressureJobs,
        v.PressureSources,v.UnknownCapacity)
}
func logAuthenticFecFailures(role string,v realityfront.V4PublicFecTxFailures,err error){
    if err!=nil{
        log.Printf("V4_PUBLIC_FEC2_FAILURE_NOT_AVAILABLE role=%s error=%v",role,err)
        return
    }
    log.Printf("V4_PUBLIC_FEC2_FAILURE role=%s source_payload=%d source_arena=%d source_seal=%d parity_policy=%d parity_arena=%d parity_seal=%d parity_m4_noncopy=%d source_m4_noncopy=%d",
        role,v.SourcePayload,v.SourceArena,v.SourceSeal,v.ParityPolicy,
        v.ParityArena,v.ParitySeal,v.ParityM4Noncopy,v.SourceM4Noncopy)
}
// No legacy 1180/1280 default record cap: deriveMTUBudget is the
// single cold-path source of the actual offer and authenticated TUN ceiling.

// One cold-path budget, in bytes. Normal data uses IPv4/TCP20+20,
// independent record31, FEC2 repair14, and optional logical Game envelope16.
// LINK20 is charged ONLY by fragmentation, not deducted from every packet.
// Auto reserves the maximum FEC2 framing even while its profile changes.
// Peer MSS/record limit can only narrow the configured/interface envelope.
func deriveMTUBudget(outer,device int,peerMSS,recordLimit uint16,
    mode realityfront.FecV2Mode,game bool)(uint16,int,error){
    if outer<576||outer>9000||device<576||peerMSS==0 {
        return 0,0,fmt.Errorf("invalid outer/device MTU or peer MSS")
    }
    wire:=min(outer,device)-40
    wire=min(wire,int(peerMSS))
    if recordLimit!=0 {wire=min(wire,int(recordLimit))}
    inner:=wire-31
    if mode==realityfront.FecV2Fixed||mode==realityfront.FecV2Auto {inner-=14}
    if game {inner-=16}
    if inner<576 {return 0,0,fmt.Errorf("effective inner MTU %d below product minimum 576 after framing; unsupported path budget",inner)}
    return uint16(wire),inner,nil
}
// A Game-FEC source uses one typed symbol byte and M3's 14-byte
// reservation INSIDE the original 16B Game envelope. Both cold and
// authenticated MTU must subtract exactly once; off path stays unchanged.
func gameFecBudget(c config,inner int)(int,error){
    if !c.gameFecEnabled{return inner,nil}
    inner-=15
    if inner<576{return 0,fmt.Errorf("Game+FEC inner MTU %d below 576",inner)}
    return inner,nil
}
// Called with authenticated record limits before Rust begins reading TUN.
// Multiple Game lanes can only lower the shared TUN MTU. No per-packet work.
func configureTunnelMTU(c config,tun *ownedTun)func(uint16,uint16,uint16)error{
    return func(peerMSS,clientLimit,serverLimit uint16)error{
        iface,err:=net.InterfaceByName(c.rawInterface)
        if err!=nil{return err}
        limit:=min(clientLimit,serverLimit)
        if limit==0{return fmt.Errorf("missing authenticated record limit")}
        wire,inner,err:=deriveMTUBudget(c.outerMTU,iface.MTU,peerMSS,limit,c.fecMode,c.gameLanes!=0)
        if err!=nil{return err}
        inner,err=gameFecBudget(c,inner)
        if err!=nil{return err}
        if inner<tun.mtu {
            if err=runIP("link","set","dev",tun.name,"mtu",strconv.Itoa(inner));err!=nil{return err}
            tun.mtu=inner
        }
        log.Printf("V4_PUBLIC_MTU role=%s mtu_budget_version=3 outer_config=%d interface=%d advertised_mss=%d peer_mss=%d local_record_cap=%d peer_record_cap=%d record_wire=%d tun_mtu=%d fec=%s lanes=%d",
            c.role,c.outerMTU,iface.MTU,faketcp.PublicV4AdvertisedMSS(),peerMSS,
            c.recordLimit,limit,wire,tun.mtu,c.fecMode,c.gameLanes)
        return nil
    }
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
    var handoffCommitted atomic.Bool
    var goPostHandoffDataCopies atomic.Uint64
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
            }else if handoffCommitted.Load()&&len(seg.Payload)!=0{
                goPostHandoffDataCopies.Add(1)
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
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
        })
    if err!=nil{return err}
    cfg:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{ServerName:c.serverName,RouteKey:c.routeKey,Timeout:15*time.Second},
        Username:c.username,Password:c.password,TunnelID:c.tunnel[:],
        ClientLimit:c.recordLimit,DesiredLanes:1,LaneID:1,Policy:policy,
    }
    if _,err=native.ConnectAuthenticatedPeer(dialCtx,assoc,cfg);err!=nil{return err}
    // Existing client product returns only after authenticated TLS detach,
    // exact Rust M4 RX attachment and native loop start.
    if assoc.State()!=faketcp.ClientAssociationDetached{
        _=native.Close()
        return fmt.Errorf("Normal client Rust M4 started without FakeTCP detach")
    }
    if e:=raw.ExcludeDetachedData(flow.PeerIP,flow.PeerPort);e!=nil{
        _=native.Close()
        return fmt.Errorf("Normal client receive ownership handoff: %w",e)
    }
    handoffCommitted.Store(true)
    log.Printf("V4_PUBLIC_GO_RX_HANDOFF role=client mode=%s filtered=1 rust_ready=1 original_send_fd_open=1",c.fecMode)
    *connected=true
    log.Printf("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client Rust_owner=active real_raw_tun=1")
    startV3ProductTimeline(ctx,"client",native.OriginalLoopPulse,native.OriginalOuterCounters)
    select{
    case <-ctx.Done():
    case err=<-errs:
    }
    log.Printf("V4_PUBLIC_GO_RX_POST_HANDOFF role=client mode=%s go_data_full_copies=%d",c.fecMode,goPostHandoffDataCopies.Load())
    counters,countErr:=native.OriginalOuterCounters()
    logAuthenticOuter("client",counters,countErr)
    cpu,cpuErr:=native.OriginalWorkerCPU()
    if cpuErr==nil {
        log.Printf("V4_PUBLIC_WORKER_CPU role=client rx_thread_cpu_ns=%d tx_thread_cpu_ns=%d",cpu.RxNs,cpu.TxNs)
    }else{
        log.Printf("V4_PUBLIC_WORKER_CPU_UNAVAILABLE role=client reason=%v",cpuErr)
    }
    if c.fecMode!=realityfront.FecV2Off {
        tx,txErr:=native.OriginalFecTxSnapshot()
        logAuthenticFecTx("client",tx,txErr)
        fail,failErr:=native.OriginalFecTxFailures()
        logAuthenticFecFailures("client",fail,failErr)
        actual,e:=native.OriginalFECReadback()
        if e!=nil {log.Printf("V4_PUBLIC_FEC2_READBACK_ERROR role=client error=%v",e)}
        if e==nil {log.Printf("V4_PUBLIC_FEC2_READBACK role=client mode=%s requested=%d applied=%d profile=%d pending=%t",actual.Mode,actual.RequestedRevision,actual.AppliedRevision,actual.Profile,actual.Pending)}
            rx,rxErr:=native.OriginalFecRxProof()
            if rxErr==nil {
                log.Printf("V4_PUBLIC_FEC2_RX_PROOF role=client source_seen=%d source_accepted=%d parity_seen=%d parity_accepted=%d systematic_candidate=%d recovered_candidate=%d systematic_tun=%d recovered_tun=%d tun_failed=%d decoder_rejected=%d admission_disabled=%d",
                    rx.SourceSeen,rx.SourceAccepted,rx.ParitySeen,rx.ParityAccepted,rx.SystematicCandidate,rx.RecoveredCandidate,rx.SystematicTun,rx.RecoveredTun,rx.TunFailed,rx.DecoderRejected,rx.AdmissionDisabled)
            }
            stage,stageErr:=native.OriginalFecM1Stage()
            if stageErr==nil {
                log.Printf("V4_PUBLIC_FEC2_M1_STAGE role=client attempted=%d queued=%d not_ready=%d error=%d oversize=%d mode_skipped=%d",
                    stage.Attempted,stage.Queued,stage.NotReady,stage.Error,
                    stage.OversizePrecheck,stage.ModeSkipped)
            }
            ingress,ingressErr:=native.OriginalFecM1Ingress()
            if ingressErr==nil {
                log.Printf("V4_PUBLIC_FEC2_M1_INGRESS role=client read_ipv4=%d small_loaned=%d small_arena_fail=%d jumbo=%d rejected=%d",
                    ingress.ReadIPv4,ingress.SmallLoaned,ingress.SmallArenaFail,
                    ingress.Jumbo,ingress.Rejected)
            }
            ip,ipErr:=native.OriginalFecRxIpClass()
            if ipErr==nil {
                log.Printf("V4_PUBLIC_FEC2_RX_IP_CLASS role=client sys_udp=%d rec_udp=%d sys_tcp=%d rec_tcp=%d other_ip=%d tcp_ack_only=%d tcp_data=%d tcp_other=%d",
                    ip.SystematicUDP,ip.RecoveredUDP,ip.SystematicTCP,ip.RecoveredTCP,
                    ip.OtherIP,ip.TCPAckOnly,ip.TCPData,ip.TCPOther)
            }
            proof,m2err:=native.OriginalFecM2Proof()
            if m2err==nil {
                firstCensored,coverCensored:=0,0
                if proof.FirstCensored{firstCensored=1}
                if proof.CoverageCensored{coverCensored=1}
                log.Printf("V4_PUBLIC_FEC2_M2_PROOF role=client accepted=%d not_sent=%d uncertain=%d unknown_2s=%d unknown_8s=%d covered_2s=%d covered_8s=%d reverse_reports=%d first_censored=%d cover_censored=%d positive_lag_ns=%d positive_samples=%d positive_mean_us=%d positive_mean_known=%t",
                    proof.Accepted,proof.NotSent,proof.Uncertain,proof.Unknown2s,proof.Unknown8s,
                    proof.Covered2s,proof.Covered8s,proof.ReverseReports,firstCensored,coverCensored,
                    proof.PositiveConfirmationLagNs,proof.PositiveConfirmationSamples,
                    proof.PositiveConfirmationMeanUs,proof.PositiveConfirmationMeanKnown)
            }
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
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
        })
    if err!=nil{return err}
    table,err:=faketcp.NewServerAssociationTable(32,emit)
    if err!=nil{return err}
    reply:=realityfront.ServerAdmissionConfig{
        TLS:realityfront.ServerConfig{ServerName:c.serverName,RouteKey:c.routeKey,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{certificate}},
            Timeout:15*time.Second},
        ExpectedUsername:c.username,ExpectedPassword:c.password,ServerLimit:c.recordLimit,
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            if len(req.TunnelID)!=16 || string(req.TunnelID)!=string(c.tunnel[:]) ||
               req.DesiredLanes!=1||req.LaneID!=1{return realityfront.ErrAdmissionParams}
            return nil
        },
    }
    errs:=make(chan error,1)
    admitted:=make(chan struct{},1)
    var handoffCommitted atomic.Bool
    var goPostHandoffDataCopies atomic.Uint64
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
                if handoffCommitted.Load(){continue}
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
                if handoffCommitted.Load()&&len(seg.Payload)!=0{
                    goPostHandoffDataCopies.Add(1)
                }
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
                        if e==nil&&ctx.Err()!=nil{e=errors.Join(ctx.Err(),product.Close())}
                        if e==nil{
                            state,exists:=assoc.TransitionState()
                            if !exists||state!=faketcp.TransitionDetached{
                                e=errors.Join(fmt.Errorf("Normal server Rust M4 started without FakeTCP detach"),product.Close())
                            }else{
                                flow:=assoc.Flow()
                                if flow.ServerIP!=c.localIP.As4()||flow.ServerPort!=c.localPort{
                                    e=errors.Join(fmt.Errorf("Normal server detached flow scope mismatch"),product.Close())
                                }else if filterErr:=raw.ExcludeDetachedData(flow.ClientIP,flow.ClientPort);filterErr!=nil{
                                    e=errors.Join(fmt.Errorf("Normal server receive ownership handoff: %w",filterErr),product.Close())
                                }
                            }
                        }
                        if e!=nil{
                            select{case errs<-e:default:}
                            return
                        }
                        handoffCommitted.Store(true)
                        log.Printf("V4_PUBLIC_GO_RX_HANDOFF role=server mode=%s filtered=1 rust_ready=1 original_send_fd_open=1",c.fecMode)
                        log.Printf("V4_ORIGINAL_GO_SERVER_NATIVE_READY role=server Rust_owner=active real_raw_tun=1")
                        startV3ProductTimeline(ctx,"server",product.OriginalLoopPulse,product.OriginalOuterCounters)
                    }()
                default:}
            }
        }
    }()
    select{case <-ctx.Done():case err=<-errs:}
    // The public product's authenticated readiness is published atomically
    // by the admission worker; only this caller writes the lifecycle flag.
    *connected=handoffCommitted.Load()
    log.Printf("V4_PUBLIC_GO_RX_POST_HANDOFF role=server mode=%s go_data_full_copies=%d",c.fecMode,goPostHandoffDataCopies.Load())
    if *connected{
        counters,countErr:=product.OriginalOuterCounters()
        logAuthenticOuter("server",counters,countErr)
        cpu,cpuErr:=product.OriginalWorkerCPU()
        if cpuErr==nil {
            log.Printf("V4_PUBLIC_WORKER_CPU role=server rx_thread_cpu_ns=%d tx_thread_cpu_ns=%d",cpu.RxNs,cpu.TxNs)
        }else{
            log.Printf("V4_PUBLIC_WORKER_CPU_UNAVAILABLE role=server reason=%v",cpuErr)
        }
        if c.fecMode!=realityfront.FecV2Off {
            tx,txErr:=product.OriginalFecTxSnapshot()
            logAuthenticFecTx("server",tx,txErr)
            fail,failErr:=product.OriginalFecTxFailures()
            logAuthenticFecFailures("server",fail,failErr)
            actual,e:=product.OriginalFECReadback()
            if e!=nil {log.Printf("V4_PUBLIC_FEC2_READBACK_ERROR role=server error=%v",e)}
            if e==nil {log.Printf("V4_PUBLIC_FEC2_READBACK role=server mode=%s requested=%d applied=%d profile=%d pending=%t",actual.Mode,actual.RequestedRevision,actual.AppliedRevision,actual.Profile,actual.Pending)}
            rx,rxErr:=product.OriginalFecRxProof()
            if rxErr==nil {
                log.Printf("V4_PUBLIC_FEC2_RX_PROOF role=server source_seen=%d source_accepted=%d parity_seen=%d parity_accepted=%d systematic_candidate=%d recovered_candidate=%d systematic_tun=%d recovered_tun=%d tun_failed=%d decoder_rejected=%d admission_disabled=%d",
                    rx.SourceSeen,rx.SourceAccepted,rx.ParitySeen,rx.ParityAccepted,rx.SystematicCandidate,rx.RecoveredCandidate,rx.SystematicTun,rx.RecoveredTun,rx.TunFailed,rx.DecoderRejected,rx.AdmissionDisabled)
            }
            stage,stageErr:=product.OriginalFecM1Stage()
            if stageErr==nil {
                log.Printf("V4_PUBLIC_FEC2_M1_STAGE role=server attempted=%d queued=%d not_ready=%d error=%d oversize=%d mode_skipped=%d",
                    stage.Attempted,stage.Queued,stage.NotReady,stage.Error,
                    stage.OversizePrecheck,stage.ModeSkipped)
            }
            ingress,ingressErr:=product.OriginalFecM1Ingress()
            if ingressErr==nil {
                log.Printf("V4_PUBLIC_FEC2_M1_INGRESS role=server read_ipv4=%d small_loaned=%d small_arena_fail=%d jumbo=%d rejected=%d",
                    ingress.ReadIPv4,ingress.SmallLoaned,ingress.SmallArenaFail,
                    ingress.Jumbo,ingress.Rejected)
            }
            ip,ipErr:=product.OriginalFecRxIpClass()
            if ipErr==nil {
                log.Printf("V4_PUBLIC_FEC2_RX_IP_CLASS role=server sys_udp=%d rec_udp=%d sys_tcp=%d rec_tcp=%d other_ip=%d tcp_ack_only=%d tcp_data=%d tcp_other=%d",
                    ip.SystematicUDP,ip.RecoveredUDP,ip.SystematicTCP,ip.RecoveredTCP,
                    ip.OtherIP,ip.TCPAckOnly,ip.TCPData,ip.TCPOther)
            }
            proof,m2err:=product.OriginalFecM2Proof()
            if m2err==nil {
                firstCensored,coverCensored:=0,0
                if proof.FirstCensored{firstCensored=1}
                if proof.CoverageCensored{coverCensored=1}
                log.Printf("V4_PUBLIC_FEC2_M2_PROOF role=server accepted=%d not_sent=%d uncertain=%d unknown_2s=%d unknown_8s=%d covered_2s=%d covered_8s=%d reverse_reports=%d first_censored=%d cover_censored=%d positive_lag_ns=%d positive_samples=%d positive_mean_us=%d positive_mean_known=%t",
                    proof.Accepted,proof.NotSent,proof.Uncertain,proof.Unknown2s,proof.Unknown8s,
                    proof.Covered2s,proof.Covered8s,proof.ReverseReports,firstCensored,coverCensored,
                    proof.PositiveConfirmationLagNs,proof.PositiveConfirmationSamples,
                    proof.PositiveConfirmationMeanUs,proof.PositiveConfirmationMeanKnown)
            }
        }
        closeErr:=product.Close()
        if closeErr==nil{log.Printf("V4_PUBLIC_NATIVE_STOP_DRAINED role=server")}
        if err!=nil{return errors.Join(err,closeErr)}
        return closeErr
    }
    return err
}
