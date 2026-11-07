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
    "crypto/x509"
    "crypto/subtle"
    "crypto/tls"
    "encoding/binary"
    "encoding/hex"
    "encoding/json"
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
    "sync"
    "sync/atomic"
    "syscall"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
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
    tlsRoots *x509.CertPool
    tlsCert string
    tlsKey string
    username string
    password string
    users map[string]string
    tunnel [16]byte
    autoIP bool
    installation [16]byte
    leasePool netip.Prefix
    manualClientLease4 netip.Prefix // server-local manual /32, authenticated generations only
    fecMode realityfront.FecV2Mode
    peerPersona realityfront.V4PublicNativePeerPersona
    fecProfile realityfront.FecV2Profile
    // Each client opts into its own original authenticated V3 record AEAD.
    // The server never supplies a process-global override for a peer.
    recordCipher uint8
    gameLanes uint8
    // Server-only one-443 protected Normal/Game2/Game4 cold acceptor.
    // Not serialized or present in FakeTCP/TLS prelude.
    mixedModes bool
    gameFecEnabled bool
    gameFecProfile uint8
    game4CopyStagger bool
    game4CopyWideStagger bool
    outerMTU int
    // Cold-only timer rotation. Zero retains the legacy disabled default.
    rotationInterval time.Duration
    rotationJitter time.Duration
    rotationGeneration uint64
    disableOuterRepair bool
    recordLimit uint16
    innerMTU int
    // Cold generation's kernel-selected path budget; zero for the older
    // non-path-supervised product. Never user-supplied or serialized.
    underlayBudgetMTU int
    // Process-scoped original Rust TUN reader. Never included in config
    // wire/user arguments; only initialized by genuine cold OS Go owner.
    sharedTun *realityfront.V4LinuxSharedTun
    // Transient generation safety: a pending new-path TLS session cannot
    // mutate an active generation's authenticated inner IPv4 address.
    leaseMustStay bool
    tunFqMaxrateMbps int
    tunTxQLenPackets int
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
    route:=flags.String("route-key-hex","","pre-shared 32-byte route key hex (64 characters); no on-wire key exchange")
    caPEM:=flags.String("tls-ca-pem","","client application-scoped trusted server CA/certificate PEM (default OS trust)")
    cert:=flags.String("tls-cert","","original server TLS PEM")
    key:=flags.String("tls-key","","original server private PEM")
    user:=flags.String("username","","original protected admission user")
    pass:=flags.String("password","","original protected admission password; prefer --password-file on shared devices")
    passFile:=flags.String("password-file","","mode-0600 regular secret file, no symlinks")
    routeFile:=flags.String("route-key-hex-file","","mode-0600 route key hex file, no symlinks")
    tunnel:=flags.String("tunnel-id","","manual 16B tunnel-id (auto-ip derives from installation)")
    autoIP:=flags.Bool("auto-ip",false,"client protected automatic IPv4 assignment")
    installPath:=flags.String("installation-id-file",".wbd-next-installation-id","portable 0600 installation identity")
    leasePool:=flags.String("lease-pool","","server memory-only 7-day IPv4 pool CIDR")
    manualLease:=flags.String("manual-client-lease4","","server-verified fixed client /32 for manual TLS generation replacement; requires tunnel-id, not a user inner MTU")
    usersFile:=flags.String("users-file","","server: 0600 JSON object username->password")
    mode:=flags.String("mode","normal","V4 normal, fec-fixed, fec-auto, game2, game4; server-only shared accepts all protected modes")
    peerPersona:=flags.String("peer-persona","legacy","expected original Go TLS peer envelope: legacy or windows11 (server-only)")
    profile:=flags.Uint("fec-profile",1,"FEC2 profile 0..6 for normal fixed; auto uses strong startup")
    cipherName:=flags.String("record-cipher","chacha20-poly1305","client authenticated V4 record AEAD: chacha20-poly1305, aes-128-gcm or aes-256-gcm")
    gameFec:=flags.String("game-fec","off","Game2/4 inner fixed FEC: off or fixed0..fixed6; BOTH authenticated endpoints must match; no Game Auto")
    game4Copy:=flags.String("game4-copy-schedule","","Game4 default stagger-4-50-140; explicit stagger-4-20-60 legacy fallback or immediate rollback; Game2 unchanged")
    outerRepair:=flags.String("outer-repair","on","outer DATA retransmission on|off; FEC parity and actual receipt feedback remain enabled")
    outerMTU:=flags.Int("outer-mtu",1460,"outer complete IPv4 IP-packet MTU in bytes (576..1500, no L2); inner TUN MTU automatic/read-only")
    rotateInterval:=flags.Duration("rotation-interval",0,"client: cold authenticated lane/group rotation on unchanged physical network (e.g. 5m); 0 disables")
    rotateJitter:=flags.Duration("rotation-jitter",0,"client: bounded random ±jitter for each rotation (e.g. 3s with --rotation-interval 18s); 0 preserves exact interval")
    tunFqRate:=flags.Int("tun-fq-maxrate-mbps",600,"owned Linux TUN per-flow fq maxrate Mbps: default 600 in all supported modes; explicit 0 disables")
    tunTxQLen:=flags.Int("tun-txqlen-packets",2048,"owned original Linux TUN TX queue: 2048 bounded default, 500 explicit rollback")
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
    if *usersFile!=""{
        if role!="server"||*user!=""||*pass!=""{return c,fmt.Errorf("users-file replaces single server credentials")}
        raw,e:=readPrivateArgFile(*usersFile)
        if e!=nil{return c,fmt.Errorf("users-file: %w",e)}
        if e=json.Unmarshal([]byte(raw),&c.users);e!=nil||len(c.users)==0||len(c.users)>256{
            return c,fmt.Errorf("users-file must be bounded nonempty JSON object")
        }
        for username,password:=range c.users{
            if len(username)<1||len(username)>128||strings.TrimSpace(username)!=username||
               len(password)<1||len(password)>512{return c,fmt.Errorf("invalid users-file credentials")}
        }
    }
    switch *mode{
    case "normal":c.fecMode=realityfront.FecV2Off
    case "fec-fixed":c.fecMode=realityfront.FecV2Fixed
    case "fec-auto":c.fecMode=realityfront.FecV2Auto
    case "game2":c.gameLanes=2;c.fecMode=realityfront.FecV2Off
    case "game4":c.gameLanes=4;c.fecMode=realityfront.FecV2Off
    case "shared":
        if role!="server"{return c,fmt.Errorf("shared protected Normal/Game mode is server-only")}
        c.mixedModes=true
        c.fecMode=realityfront.FecV2Off
    default:return c,fmt.Errorf("V4 mode %q not installed in native public owner",*mode)
    }
    switch *peerPersona{
    case "legacy":c.peerPersona=realityfront.V4PeerLegacy
    case "windows11":
        if role!="server"{return c,fmt.Errorf("windows11 peer persona requires original Go server")}
        c.peerPersona=realityfront.V4PeerWindows11
    default:return c,fmt.Errorf("unsupported trusted peer persona %q",*peerPersona)
    }
    if *profile>6{return c,fmt.Errorf("fec-profile must be 0..6")}
    selected,e:=realityfront.ParseRecordCipherName(*cipherName)
    if e!=nil{return c,fmt.Errorf("record-cipher must be chacha20-poly1305, aes-128-gcm or aes-256-gcm: %w",e)}
    if role=="server"&&selected!=realityfront.CipherChaCha{
        return c,fmt.Errorf("record-cipher is per authenticated client; server cannot force a global V4 cipher")
    }
    c.recordCipher=selected
    if *gameFec!="off"{
        if c.gameLanes==0||len(*gameFec)!=6||!strings.HasPrefix(*gameFec,"fixed")||
           (*gameFec)[5]<'0'||(*gameFec)[5]>'6'{
            return c,fmt.Errorf("game-fec must be off or fixed0..fixed6 on game2/game4")
        }
        c.gameFecEnabled=true
        c.gameFecProfile=uint8((*gameFec)[5]-'0')
    }
    if *game4Copy=="" {
        if c.gameLanes==4 {*game4Copy="stagger-4-50-140"
        } else {*game4Copy="immediate"}
    }
    switch *game4Copy{
    case "immediate":
    case "stagger-4-20-60","stagger-4-50-140":
        if c.gameLanes!=4{
            return c,fmt.Errorf("game4-copy-schedule stagger requires game4")
        }
        c.game4CopyStagger=true
        c.game4CopyWideStagger=*game4Copy=="stagger-4-50-140"
    default:return c,fmt.Errorf("game4-copy-schedule must be immediate, stagger-4-20-60 or stagger-4-50-140")
    }
    if *outerMTU<576||*outerMTU>1500{return c,fmt.Errorf("outer-mtu public IPv4 range is 576..1500; jumbo is experimental/unsupported")}
    if err:=validateOriginalRotationPolicy(role,*rotateInterval,*rotateJitter);err!=nil{return c,err}
    // User authorized product-owned fq600 for ALL Linux public modes:
    // Normal/off, FEC Fixed/Auto, Game2/Game4. It is applied only after
    // creating our ephemeral TUN; explicit0 remains a safe rollback.
    if *tunFqRate!=0 && *tunFqRate!=600 {
        return c,fmt.Errorf("tun-fq-maxrate-mbps must be 0 or 600")
    }
    c.tunFqMaxrateMbps=*tunFqRate
    if *tunTxQLen!=500&&*tunTxQLen!=2048{return c,fmt.Errorf("tun-txqlen-packets must be 500 or 2048")}
    c.tunTxQLenPackets=*tunTxQLen
    switch *outerRepair{
    case "on":c.disableOuterRepair=false
    case "off":c.disableOuterRepair=true
    default:return c,fmt.Errorf("outer-repair must be on or off")
    }
    c.outerMTU=*outerMTU
    c.rotationInterval=*rotateInterval
    c.rotationJitter=*rotateJitter
    c.autoIP=*autoIP
    if role=="server"{
        if c.autoIP{return c,fmt.Errorf("auto-ip client-only; configure server lease-pool")}
        if *leasePool!=""{
            prefix,e:=netip.ParsePrefix(*leasePool)
            if e!=nil||!prefix.Addr().Is4()||prefix.Bits()>30||prefix.Bits()<1{
                return c,fmt.Errorf("lease-pool requires bounded IPv4 CIDR")
            }
            c.leasePool=prefix.Masked()
        }
        if *manualLease!=""{
            if *leasePool!=""{return c,fmt.Errorf("manual-client-lease4 and lease-pool are mutually exclusive")}
            p,e:=netip.ParsePrefix(*manualLease)
            if e!=nil||!p.Addr().Is4()||p.Bits()!=32||
                p.Addr().IsUnspecified()||p.Addr().IsMulticast()||
                p.Addr().IsLoopback()||p.Addr().IsLinkLocalUnicast(){
                return c,fmt.Errorf("manual-client-lease4 requires one server-provisioned valid IPv4 /32")
            }
            c.manualClientLease4=p
        }
    }else if *usersFile!=""||*leasePool!=""||*manualLease!=""{
        return c,fmt.Errorf("users-file/lease-pool/manual-client-lease4 server-only")
    }
    c.fecProfile=realityfront.FecV2Profile(*profile)
    if role=="client"&&c.autoIP&&*tunCIDR==""{*tunCIDR="169.254.240.1/32"}
    validCredentials:=*user!=""&&*pass!=""
    if role=="server"&&len(c.users)>0{validCredentials=true}
    if *iface==""||len(*tunName)==0||len(*tunName)>15||
       *tunCIDR==""||*name==""||!validCredentials||
       *port==0||*port>65535||(len(*route)>0&&len(*route)<32){
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
    if err!=nil||len(c.routeKey)!=32{
        return c,fmt.Errorf("offline 32-byte route-key is required locally (64 hex characters); no network key bootstrap")
    }
    if role=="server"&&*caPEM!=""{
        return c,fmt.Errorf("tls-ca-pem is a client-only setting; server uses tls-cert and tls-key")
    }
    if role=="client"&&*caPEM!=""{
        pem,e:=os.ReadFile(*caPEM)
        if e!=nil{return c,fmt.Errorf("load server TLS trust PEM: %w",e)}
        if len(pem)==0||len(pem)>1<<20{return c,fmt.Errorf("invalid TLS trust PEM size")}
        roots:=x509.NewCertPool()
        if !roots.AppendCertsFromPEM(pem){return c,fmt.Errorf("trusted server TLS PEM contains no certificate")}
        c.tlsRoots=roots
    }
    if role=="client"&&c.autoIP{
        if *tunnel!=""||*installPath==""{return c,fmt.Errorf("auto-ip derives tunnel ID, do not pass manual ID")}
        installation,e:=logicaltunnel.ResolveInstallation("",*installPath,false)
        if e!=nil{return c,fmt.Errorf("installation-id-file: %w",e)}
        c.installation=installation
        c.tunnel=logicaltunnel.DerivedTunnelID(c.username,installation)
    }else if *tunnel!=""{
        raw,e:=hex.DecodeString(*tunnel)
        if e!=nil||len(raw)!=16{return c,fmt.Errorf("invalid manual tunnel-id")}
        copy(c.tunnel[:],raw)
    }
    if c.tunnel==[16]byte{}&&!(role=="server"&&c.leasePool.IsValid()){
        return c,fmt.Errorf("manual tunnel-id required without auto-IP/lease-pool")
    }
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
    tunPrefix,e:=netip.ParsePrefix(*tunCIDR)
    if e!=nil||!tunPrefix.Addr().Is4(){return c,fmt.Errorf("invalid tun-ipv4")}
    if role=="server"&&c.manualClientLease4.IsValid(){
        if !tunPrefix.Contains(c.manualClientLease4.Addr())||
           c.manualClientLease4.Addr()==tunPrefix.Addr(){
            return c,fmt.Errorf("manual client /32 must be distinct from server TUN IPv4 inside its owned subnet")
        }
    }
    if role=="server"&&c.leasePool.IsValid(){
        if !tunPrefix.Contains(c.leasePool.Addr())||
           tunPrefix.Bits()>c.leasePool.Bits()||
           c.leasePool.Contains(tunPrefix.Addr()){
            return c,fmt.Errorf("server tun-ipv4 must route the whole client pool but reserve its own IP outside the pool")
        }
    }
    return c,nil
}
func runIP(args ...string)error{
    cmd:=exec.Command("ip",args...)
    output,err:=cmd.CombinedOutput()
    if err!=nil{return fmt.Errorf("owned Linux ip %v: %w %s",args,err,output)}
    return nil
}
// Only the original Go owner of a newly-created TUN may resize its TX
// queue, once before protected Rust workers can write. The old Linux kernel
// qlen500 dropped 594 packets at 100Mbps, matching 597 Windows business
// first-source gaps; owned qlen2048 twice produced zero TUN TX drops.
func validateOwnedTunTxQueueReadback(raw []byte,name string,packets int)error{
    var links []struct{
        IfName string `json:"ifname"`
        IfIndex int `json:"ifindex"`
        MTU int `json:"mtu"`
        QLen int `json:"txqlen"`
        LinkType string `json:"link_type"`
        Flags []string `json:"flags"`
    }
    if err:=json.Unmarshal(raw,&links);err!=nil{return fmt.Errorf("TUN tx queue JSON readback: %w",err)}
    if len(links)!=1||links[0].IfName!=name||links[0].IfIndex<=0||
       links[0].MTU<576||links[0].MTU>1500||links[0].QLen!=packets||
       links[0].LinkType!="none"{return fmt.Errorf("original Linux TUN tx queue identity mismatch")}
    seen:=map[string]bool{}
    for _,flag:=range links[0].Flags{seen[flag]=true}
    if !seen["UP"]||!seen["POINTOPOINT"]||!seen["NOARP"]{
        return fmt.Errorf("original Linux TUN tx queue flag readback mismatch")
    }
    return nil
}
func setOwnedTunTxQueue(name string,packets int)error{
    if packets!=500&&packets!=2048{return fmt.Errorf("unsupported bounded owned TUN txqlen %d",packets)}
    if err:=runIP("link","set","dev",name,"txqueuelen",strconv.Itoa(packets));err!=nil{return err}
    raw,err:=exec.Command("ip","-j","link","show","dev",name).CombinedOutput()
    if err!=nil{return fmt.Errorf("owned TUN queue readback: %w %s",err,raw)}
    return validateOwnedTunTxQueueReadback(raw,name,packets)
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
// A real iproute2 readback is a receipt, not the planned Rust budget.
// This is cold setup/reconfiguration only; never called on packet hot path.
func validateOwnedTunMTUReadback(raw []byte,name string)(int,error){
 var links []struct{
  IfName string `json:"ifname"`
  IfIndex int `json:"ifindex"`
  MTU int `json:"mtu"`
  LinkType string `json:"link_type"`
 }
 if err:=json.Unmarshal(raw,&links);err!=nil{return 0,fmt.Errorf("TUN MTU JSON: %w",err)}
 if len(links)!=1||links[0].IfName!=name||links[0].IfIndex<=0||
  links[0].LinkType!="none"||links[0].MTU<576||links[0].MTU>1500{
  return 0,fmt.Errorf("owned TUN MTU OS identity/size mismatch")
 }
 return links[0].MTU,nil
}
func readOwnedTunMTU(name string)(int,error){
 raw,err:=exec.Command("ip","-j","link","show","dev",name).CombinedOutput()
 if err!=nil{return 0,fmt.Errorf("owned TUN MTU readback: %w: %s",err,raw)}
 return validateOwnedTunMTUReadback(raw,name)
}
type ownedTun struct{
    f *os.File
    name string
    cidr string
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
    device:=&ownedTun{f:fd,name:name,cidr:cidr,mtu:mtu}
    // This public TUN is IPv4-only. At MTU>=1280 Linux would otherwise create
    // IPv6 link-local/RS traffic, which the IPv4 driver correctly rejects.
    // Set only our newly-owned device, before bringing it up; no host sysctl.
    err=os.WriteFile("/proc/sys/net/ipv6/conf/"+name+"/disable_ipv6",[]byte("1\n"),0)
    if err!=nil&&!errors.Is(err,os.ErrNotExist){_ = device.Close();return nil,err}
    if err=runIP("addr","add",cidr,"dev",name);err==nil{
        err=runIP("link","set","dev",name,"mtu",strconv.Itoa(mtu),"up")
    }
    if err==nil {
        var applied int
        applied,err=readOwnedTunMTU(name)
        if err==nil&&applied!=mtu {err=fmt.Errorf("owned TUN OS-applied MTU mismatch requested=%d actual=%d",mtu,applied)}
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
var errPublicNativePeerDead=errors.New("original Rust authenticated peer dead; Go cold TLS reauthorization required")

// Only after authenticated Rust HealthClock dead AND a real TUN wake may the
// original Go cold client retry a transient TLS/FakeTCP timeout. This never
// retries a rejected credential, certificate or protocol invariant error,
// and never changes the Rust data/PN/MTU owner or one-use ciphertext.
func nativeColdTLSRetryable(err error)bool{
    if errors.Is(err,context.DeadlineExceeded)||errors.Is(err,syscall.ETIMEDOUT)||
       errors.Is(err,faketcp.ErrBootstrapTimeout){return true}
    var ne net.Error
    return errors.As(err,&ne)&&ne.Timeout()
}
// Original FakeTCP WaitEstablished only observes state: it does not drive
// SYN retransmission. The first cold SYN can precede peer server readiness.
// Advance its ORIGINAL bounded 1s RTO/MaxSYNRetries on the Go cold path only.
func waitForOriginalColdSYN(ctx context.Context,assoc *faketcp.ClientAssociation)error{
    for {
        stepCtx,stop:=context.WithTimeout(ctx,time.Second)
        e:=assoc.WaitEstablished(stepCtx)
        stop()
        if e==nil{return nil}
        if ctx.Err()!=nil{return ctx.Err()}
        if !errors.Is(e,context.DeadlineExceeded){return e}
        if _,e=assoc.EmitRetransmitDue(time.Now());e!=nil{return e}
    }
}
// A genuine original FakeTCP ClientAssociation drives SYN RTO while cold
// establishing, but the synchronous protected TLS Write/Read stage also
// needs its already-implemented Sender.RetransmitDue. A missing client
// cumulative ACK or DATA segment otherwise waits for the 15s absolute TLS
// deadline without a single sender retransmission under 15-30% netem loss.
//
// This ONLY polls the existing original sender while Established. Sender
// chooses its own RTO, backoff, original seq/ACK/payload, peer window and
// segment quotas. No new wire data, crypto, M4 DATA, timer owner after Detach,
// extra controller or extended authentication deadline is introduced.
func driveOriginalClientColdBootstrapRTO(
    ctx context.Context,assoc *faketcp.ClientAssociation,
)func()(uint64,error){
    scoped,cancel:=context.WithCancel(ctx)
    type result struct{ count uint64; err error }
    done:=make(chan result,1)
    go func(){
        ticker:=time.NewTicker(100*time.Millisecond)
        defer ticker.Stop()
        var count uint64
        for{
            select{
            case <-scoped.Done():done<-result{count:count};return
            case <-ticker.C:
            }
            switch assoc.State(){
            case faketcp.ClientAssociationDetached,faketcp.ClientAssociationClosed:
                done<-result{count:count}
                return
            case faketcp.ClientAssociationEstablished:
                resent,err:=assoc.EmitRetransmitDue(time.Now())
                if err!=nil{done<-result{count:count,err:err};return}
                if resent{count++}
            }
        }
    }()
    var once sync.Once
    var out result
    return func()(uint64,error){
        once.Do(func(){cancel();out=<-done})
        return out.count,out.err
    }
}

func originalColdRetryAllowed(role string,authorized,ready bool,retries int,runErr,closeErr error)bool{
    return role=="client"&&authorized&&!ready&&retries<2&&closeErr==nil&&nativeColdTLSRetryable(runErr)
}
func nativeColdFailureClass(err error)string{
    if nativeColdTLSRetryable(err){return "timeout"}
    if errors.Is(err,context.Canceled){return "cancelled"}
    if errors.Is(err,io.EOF){return "eof"}
    return "other"
}

// Rust alone owns native Health. Go cold control must never mistake a
// cumulative raw M4 NotSent, transient backpressure, or optional feedback
// scheduling error for 90s of missing authenticated peer activity.
// Only the exact Rust HealthClock terminal flag can reauthorize TLS.
func publicNativeHealthDead(p realityfront.V4PublicLoopPulse)bool{
 return p.AuthenticatedPeerDead
}
func monitorPublicNativePeer(ctx context.Context,errs <-chan error,
 live func()bool,pulse func()(realityfront.V4PublicLoopPulse,error))error{
 ticker:=time.NewTicker(time.Second);defer ticker.Stop()
 for{select{
 case <-ctx.Done():return nil
 case e:=<-errs:return e
 case <-ticker.C:
  if live(){stats,e:=pulse();if e==nil&&publicNativeHealthDead(stats){return errPublicNativePeerDead}}
 }}
}

// Cold only: wait for real kernel TUN READABILITY after old Rust Stop/join;
// do not consume a single source. The newly authorized owner reads it.
func waitForNativeReconnectTraffic(ctx context.Context,tun *ownedTun)error{
 fd:=int(tun.f.Fd())
 if fd<0||fd>=1024{return fmt.Errorf("reconnect TUN fd outside select bound %d",fd)}
 for{
  if e:=ctx.Err();e!=nil{return e}
  var rfds syscall.FdSet;rfds.Bits[fd/64]|=int64(1)<<uint(fd%64)
  wait:=syscall.Timeval{Sec:1}
  n,e:=syscall.Select(fd+1,&rfds,nil,nil,&wait)
  if errors.Is(e,syscall.EINTR){continue}
  if e!=nil{return fmt.Errorf("reconnect TUN readiness: %w",e)}
  if n>0{return nil}
 }
}

func productNativeCleanup(c config,tun *ownedTun)func()error{
 // Every Normal off/Fixed/Auto generation can enter the same authenticated
 // dead90 reauthorization path. Rust Stop joins its workers; the original Go
 // Run owner retains the same TUN between generations and closes on final exit.
 // Game has its separate grouped lifetime and never calls this helper.
 return func()error{return nil}
}

// Offline initialization: create a fresh 32B server entry-recognition key
// exactly once, owner-only and no symlink/overwrite. The secret is NEVER
// placed on stdout or in argv. Client imports the file via an offline channel.
func initServerRouteKeyFile(path string)error{
 if path==""{return fmt.Errorf("missing destination for server route-key initialization")}
 var key [32]byte
 if _,err:=rand.Read(key[:]);err!=nil{return err}
 fd,err:=syscall.Open(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL|syscall.O_CLOEXEC|syscall.O_NOFOLLOW,0600)
 if err!=nil{return fmt.Errorf("create route-key file without overwrite: %w",err)}
 f:=os.NewFile(uintptr(fd),"generated-route-key")
 _,err=f.WriteString(hex.EncodeToString(key[:])+"\n")
 if e:=f.Sync();err==nil{err=e}
 if e:=f.Close();err==nil{err=e}
 if err!=nil{return err}
 log.Print("V4_PUBLIC_ROUTE_KEY_GENERATED local_file_only=1 bytes=32 permissions=0600")
 return nil
}
func Run(role string,args []string)(retErr error){
 if role=="server"&&len(args)==2&&args[0]=="--init-route-key-file"{
   return initServerRouteKeyFile(args[1])
 }
 cfg,err:=parse(role,args)
    if err!=nil{return err}
    iface,err:=net.InterfaceByName(cfg.rawInterface)
    if err!=nil{return err}
    // Product SYN MSS and initial record offer are computed from the same
    // real cold outer/interface envelope. No inherited 1360/1280 ceiling.
    // Pure Rust pre-TLS derives the advertised SYN ceiling from the same
    // outer/device units as the authenticated data record budget.
    coldBudget,err:=realityfront.V4DeriveColdMTUBudget(realityfront.V4ColdMTUBudgetInput{
        ConfiguredOuterIPMTU:uint32(cfg.outerMTU),PhysicalOuterIPMTU:uint32(iface.MTU),
        IPv4HeaderBytes:20,TCPDataHeaderBytes:20,Mode:0,
    })
    if err!=nil{return err}
    publicMSS:=int(coldBudget.LocalSYNAdvertisedMSS)
    if publicMSS<536||publicMSS>1460{return fmt.Errorf("unsupported public IPv4 MSS %d",publicMSS)}
    if err=faketcp.SetPublicV4AdvertisedMSS(uint16(publicMSS));err!=nil{return err}
    cfg.recordLimit,cfg.innerMTU,err=deriveMTUBudget(cfg.outerMTU,iface.MTU,
        uint16(publicMSS),0,cfg.fecMode,cfg.gameLanes!=0,cfg.gameFecEnabled)
    if err!=nil{return err}
    log.Printf("V4_PUBLIC_MTU_PREPARE role=%s mtu_budget_version=3 outer_config=%d interface=%d advertised_mss=%d record_offer=%d tun_planned=%d",cfg.role,cfg.outerMTU,iface.MTU,publicMSS,cfg.recordLimit,cfg.innerMTU)
    tun,err:=openTun(cfg.tunName,cfg.tunCIDR,cfg.innerMTU)
    if err!=nil{return err}
    // The Go cold lifetime owns TUN; each Rust generation Stop joins and
    // releases kernel loans before the FINAL Go close or a fresh TLS generation.
    connected:=false
    defer func(){_ = tun.Close()}()
    if err=setOwnedTunTxQueue(tun.name,cfg.tunTxQLenPackets);err!=nil{return err}
    log.Printf("V4_PUBLIC_TUN_TXQLEN role=%s interface=%s packets=%d readback=REAL_ORIGINAL_LINUX_TUN",cfg.role,tun.name,cfg.tunTxQLenPackets)
    if err=setOwnedTunFq(tun.name,cfg.tunFqMaxrateMbps);err!=nil{return err}
    if cfg.tunFqMaxrateMbps!=0 {
        log.Printf("V4_PUBLIC_TUN_FQ role=%s interface=%s maxrate_mbps=600 flow_limit_packets=256 readback=kernel_fq_600Mbit",cfg.role,tun.name)
    } else {
        log.Printf("V4_PUBLIC_TUN_FQ role=%s interface=%s maxrate_mbps=0 readback=kernel_default",cfg.role,tun.name)
    }
    var leases *logicaltunnel.LeaseRegistry
    var epochs *realityfront.V4EpochStore
    if role=="server"{
        epochs,err=realityfront.NewV4EpochStore(4096)
        if err!=nil{return err}
        if cfg.leasePool.IsValid(){
            leases,err=logicaltunnel.NewLeaseRegistry(cfg.leasePool,4096)
            if err!=nil{return err}
            // Original 7-day lease may recycle INACTIVE devices, but never
            // a live or pending Go TLS/Rust session. The callback runs only
            // on cold authenticated allocation, never on packet hot paths.
            leases.BeforeExpire=func(id logicaltunnel.TunnelID)bool{
                return !epochs.HasLiveTunnel(id)
            }
        }
    }
    // Both Normal and Game auto-/32 use ONE process-wide native Rust
    // reader, even while old A and new B independently own their raw
    // Game/Normal M4 drivers. No additional TUN fd or Go packet pump.
    if role=="client"&&cfg.autoIP{
        shared,e:=realityfront.NewV4LinuxSharedTun(tun.f,cfg.tunName)
        if e!=nil{return e}
        cfg.sharedTun=shared
        defer func(){
            if e:=shared.Close();e!=nil{
                retErr=errors.Join(retErr,e)
                log.Printf("V4_PUBLIC_SHARED_TUN_STOP_INCOMPLETE role=client error=%v",e)
            }else{
                log.Printf("V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client")
            }
        }()
        log.Printf("V4_PUBLIC_SHARED_TUN_READER_READY role=client auto_lease=1 owner=rust_single_kernel_reader game_lanes=%d",cfg.gameLanes)
    }
    if cfg.gameLanes!=0||(role=="server"&&cfg.mixedModes){
        ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
        defer stop()
        if role=="client"&&cfg.autoIP{
            // Shared native reader atomically promotes B after authenticated
            // Game M4 Ready; A retains old business until that promotion.
            return runOriginalLinuxClientPaths(ctx,cfg,tun)
        }
        return runGame(ctx,cfg,uint32(iface.Index),tun,leases,epochs,&connected)
    }
    ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
    defer stop()
    if role=="client"&&cfg.autoIP{
        // PLAN028 only for real protected automatic IPv4 on Linux Normal.
        // The one process-shared Rust TUN reader already exists above and
        // remains owned across simultaneous A+B TLS/native generations.
        return runOriginalLinuxClientPaths(ctx,cfg,tun)
    }
    reauthAuthorized:=false
    coldRetries:=0
    for attempt:=uint64(1);;attempt++{
        if ctx.Err()!=nil{return nil}
        raw,err:=faketcp.OpenRawIPv4EndpointWithOptions(
            cfg.rawInterface,cfg.localIP.As4(),faketcp.PacketPersonaLegacy,
            faketcp.RawIPv4EndpointOptions{ReceivePort:cfg.localPort},
        )
        if err!=nil{return err}
        // Real AF_PACKET endpoint is now bound to the configured local
        // port. The netns harness must not equate an earlier TUN file
        // with a listening FakeTCP server (SYN startup race).
        log.Printf("V4_PUBLIC_RAW_AF_PACKET_READY role=%s attempt=%d interface=%s port=%d",role,attempt,cfg.rawInterface,cfg.localPort)
        emit:=func(seg faketcp.Segment)error{
            if seg.Flags&faketcp.FlagSYN!=0{
                wire:=faketcp.MarshalSegment(seg,1,faketcp.PacketPersonaLegacy)
                parsed,e:=faketcp.ParseIPv4TCP(wire)
                if e!=nil||!parsed.MSSSet||parsed.MSS!=faketcp.PublicV4AdvertisedMSS(){
                    return fmt.Errorf("original current V4 SYN MSS actual bytes inconsistent")
                }
                kind:="SYN";if seg.Flags&faketcp.FlagACK!=0{kind="SYNACK"}
                log.Printf("V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=%s generation=%d kind=%s local_advertised_mss=%d tcp_option_bytes=%x",role,attempt,kind,parsed.MSS,wire[40:44])
            }
            _,e:=raw.WriteSegment(seg);return e
        }
        connected=false
        var runErr error
        if role=="client"{
            runErr=runClient(ctx,cfg,uint32(iface.Index),tun,raw,emit,reauthAuthorized,&connected)
        }else{
            runErr=runServer(ctx,cfg,uint32(iface.Index),tun,raw,emit,leases,epochs,reauthAuthorized,&connected)
        }
        closeErr:=raw.Close()
        if reauthAuthorized&&ctx.Err()==nil&&runErr!=nil&&
           !errors.Is(runErr,errPublicNativePeerDead){
            retry:=originalColdRetryAllowed(role,reauthAuthorized,connected,coldRetries,runErr,closeErr)
            log.Printf("V4_PUBLIC_NATIVE_COLD_TLS_RESULT role=%s attempt=%d class=%s retry=%t",
                role,attempt,nativeColdFailureClass(runErr),retry)
            if retry{
                coldRetries++
                select{case <-ctx.Done():return nil
                case <-time.After(2*time.Second):}
                continue
            }
        }
        if !errors.Is(runErr,errPublicNativePeerDead)||ctx.Err()!=nil{
            return errors.Join(runErr,closeErr)
        }
        if closeErr!=nil{return closeErr}
        reauthAuthorized=true
        coldRetries=0
        log.Printf("V4_PUBLIC_COLD_STAGE role=%s stage=dead_drained unix_ms=%d",role,time.Now().UnixMilli())
        log.Printf("V4_PUBLIC_NATIVE_DEAD_RECONNECT_ARMED role=%s generation=%d old_owner_drained=1",role,attempt)
        if role=="client"{
            if e:=waitForNativeReconnectTraffic(ctx,tun);e!=nil{
                if ctx.Err()!=nil{return nil}
                return e
            }
            log.Printf("V4_PUBLIC_COLD_STAGE role=client stage=tun_trigger unix_ms=%d",time.Now().UnixMilli())
            log.Printf("V4_PUBLIC_NATIVE_RECONNECT_TRIGGER role=client source=real_kernel_tun_ready generation=%d",attempt+1)
        }
        log.Printf("V4_PUBLIC_ORIGINAL_GO_TLS_REAUTHORIZE role=%s generation=%d",role,attempt+1)
    }
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

// Rust is the sole V4 codec/mode budget oracle. This Go cold helper never
// subtracts a second FEC/Game/type byte. The optional final bool is GameFEC
// for old helper callers; public product always passes it explicitly.
func deriveMTUBudget(outer,device int,peerMSS,recordLimit uint16,
 mode realityfront.FecV2Mode,game bool,gameFEC ...bool)(uint16,int,error){
 if outer<576||outer>1500||device<576||peerMSS==0{
  return 0,0,fmt.Errorf("invalid public outer/device MTU or raw peer MSS")
 }
 if len(gameFEC)>1{return 0,0,fmt.Errorf("ambiguous GameFEC budget")}
 fec:=mode==realityfront.FecV2Fixed||mode==realityfront.FecV2Auto
 if fec&&game{return 0,0,fmt.Errorf("Game and Normal FEC mode cannot combine")}
 gameFecOn:=len(gameFEC)==1&&gameFEC[0]
 if gameFecOn&&!game{return 0,0,fmt.Errorf("GameFEC needs game lanes")}
 var modeID uint32
 switch{
 case gameFecOn:modeID=3
 case game:modeID=2
 case fec:modeID=1
 default:modeID=0
 }
 b,err:=realityfront.V4DeriveColdMTUBudget(realityfront.V4ColdMTUBudgetInput{
  ConfiguredOuterIPMTU:uint32(outer),PhysicalOuterIPMTU:uint32(device),
  PeerAdvertisedMSS:uint32(peerMSS),AgreedRecordWireCap:uint32(recordLimit),
  IPv4HeaderBytes:20,TCPDataHeaderBytes:20,Mode:modeID,
 })
 if err!=nil{return 0,0,err}
 if b.SingleInnerIPCap<576{
  return 0,0,fmt.Errorf("effective inner IP MTU %d below product floor 576",b.SingleInnerIPCap)
 }
 return uint16(b.RecordWireCap),int(b.SingleInnerIPCap),nil
}
// The authenticated-MTU callback must use the SAME cold kernel path budget
// as the SYN/record offer. Reading only iface.MTU would discard a stricter
// destination-route MTU and break source-locked path handover.
func originalNativeDeviceMTU(c config,interfaceMTU int)(int,error){
    if interfaceMTU<576||interfaceMTU>65535{
        return 0,fmt.Errorf("invalid kernel interface MTU")
    }
    if c.underlayBudgetMTU==0{return interfaceMTU,nil}
    if c.underlayBudgetMTU<576||c.underlayBudgetMTU>65535{
        return 0,fmt.Errorf("invalid kernel-selected path MTU")
    }
    return min(interfaceMTU,c.underlayBudgetMTU),nil
}
// Called with authenticated record limits before Rust begins reading TUN.
// Multiple Game lanes can only lower the shared TUN MTU. No per-packet work.
func configureTunnelMTU(c config,tun *ownedTun)func(uint16,uint16,uint16)error{
    return func(peerMSS,clientLimit,serverLimit uint16)error{
        iface,err:=net.InterfaceByName(c.rawInterface)
        if err!=nil{return err}
        limit:=min(clientLimit,serverLimit)
        if limit==0{return fmt.Errorf("missing authenticated record limit")}
        deviceMTU,err:=originalNativeDeviceMTU(c,iface.MTU)
        if err!=nil{return err}
        wire,inner,err:=deriveMTUBudget(c.outerMTU,deviceMTU,peerMSS,limit,c.fecMode,c.gameLanes!=0,c.gameFecEnabled)
        if err!=nil{return err}
        if inner!=tun.mtu {
            if err=runIP("link","set","dev",tun.name,"mtu",strconv.Itoa(inner));err!=nil{return err}
        }
        applied,err:=readOwnedTunMTU(tun.name)
        if err!=nil{return err}
        if applied!=inner{return fmt.Errorf("owned TUN OS-applied MTU mismatch requested=%d actual=%d",inner,applied)}
        tun.mtu=applied
        log.Printf("V4_PUBLIC_MTU role=%s mtu_budget_version=3 outer_config=%d interface=%d advertised_mss=%d peer_mss=%d local_record_cap=%d peer_record_cap=%d record_wire=%d tun_mtu=%d fec=%s lanes=%d path_budget_mtu=%d",
            c.role,c.outerMTU,iface.MTU,faketcp.PublicV4AdvertisedMSS(),peerMSS,
            c.recordLimit,limit,wire,tun.mtu,c.fecMode,c.gameLanes,deviceMTU)
        return nil
    }
}

// Account selection happens only after the original marker and genuine TLS
// protected request. Never derive a public pre-TLS verifier from a password.
func originalV4CredentialCheck(c config)func(string,string)bool{
    if len(c.users)==0{return nil}
    return func(username,password string)bool{
        secret,ok:=c.users[username]
        return ok&&subtle.ConstantTimeCompare([]byte(secret),[]byte(password))==1
    }
}
func originalV4AutomaticLease(reg *logicaltunnel.LeaseRegistry)func(realityfront.AdmissionRequest)(string,error){
    if reg==nil{return nil}
    return func(req realityfront.AdmissionRequest)(string,error){
        return realityfront.V4AllocateAutomaticLease(reg,req)
    }
}
// The Linux kernel must confirm the exact authenticated /32 before Rust can
// read or write the TUN. No user-controlled inner-MTU setting is introduced.
func readOwnedTunIPv4(name string)(netip.Prefix,error){
    data,err:=exec.Command("ip","-j","addr","show","dev",name).CombinedOutput()
    if err!=nil{return netip.Prefix{},fmt.Errorf("owned TUN IP readback: %w %s",err,data)}
    var links []struct{
        IfName string `json:"ifname"`
        IfIndex int `json:"ifindex"`
        AddrInfo []struct{
            Family string `json:"family"`
            Local string `json:"local"`
            PrefixLen int `json:"prefixlen"`
        } `json:"addr_info"`
    }
    if err:=json.Unmarshal(data,&links);err!=nil{return netip.Prefix{},err}
    if len(links)!=1||links[0].IfName!=name||links[0].IfIndex<=0{
        return netip.Prefix{},fmt.Errorf("owned TUN IP device identity mismatch")
    }
    var address netip.Prefix
    for _,item:=range links[0].AddrInfo{
        if item.Family!="inet"{continue}
        ip,e:=netip.ParseAddr(item.Local)
        if e!=nil||!ip.Is4()||item.PrefixLen!=32||address.IsValid(){
            return netip.Prefix{},fmt.Errorf("owned TUN IPv4 address set invalid")
        }
        address=netip.PrefixFrom(ip,32)
    }
    if !address.IsValid(){return netip.Prefix{},fmt.Errorf("owned TUN lacks IPv4")}
    return address,nil
}
func configureAuthenticatedClientIPv4(tun *ownedTun)func(string)error{
    return func(lease string)error{
        prefix,err:=netip.ParsePrefix(lease)
        if err!=nil||!prefix.Addr().Is4()||prefix.Bits()!=32||
           prefix.Addr().IsUnspecified()||prefix.Addr().IsMulticast(){
            return fmt.Errorf("invalid authenticated IPv4 lease")
        }
        desired:=prefix.String()
        if tun.cidr!=desired{
            if err:=runIP("addr","add",desired,"dev",tun.name);err!=nil{return err}
            if err:=runIP("addr","del",tun.cidr,"dev",tun.name);err!=nil{return err}
        }
        actual,err:=readOwnedTunIPv4(tun.name)
        if err!=nil{return err}
        if actual!=prefix{return fmt.Errorf("client authenticated IPv4 OS readback mismatch")}
        tun.cidr=desired
        log.Printf("V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=%s",desired)
        return nil
    }
}

// Two-phase original M4 handoff: local protected TLS/Rust start is NOT
// a remote native Commit. Require this exact candidate's authenticated
// M4 reverse IPv4 TUN delivery, OR a verified canonical native Normal/Game
// Health kind0 cold Commit receipt sent only after the server's whole
// authenticated M4 group has installed. No synthetic TCP ACK, TLS local
// READY, Go packet pump or new steady-state control wire is evidence.
// A failed server M4 leaves A intact; no Go DATA copies, new control wire,
// unauthenticated timer ownership or unbounded overlap is authorized.
func waitOriginalNativeM4PeerProof(
    ctx context.Context,pulse func()(realityfront.V4PublicLoopPulse,error),
    promote func()error,max time.Duration,
)error{
    if ctx==nil||pulse==nil||promote==nil||max<=0{
        return fmt.Errorf("invalid original authenticated M4 proof barrier")
    }
    timer:=time.NewTimer(max)
    ticker:=time.NewTicker(25*time.Millisecond)
    defer timer.Stop()
    defer ticker.Stop()
    for{
        status,err:=pulse()
        if err!=nil{return fmt.Errorf("native peer M4 evidence: %w",err)}
        if status.AuthenticatedPeerDead{
            return fmt.Errorf("candidate native authenticated peer terminal before M4 proof")
        }
        if status.RxRecords>0||status.AuthenticatedPeerControl{
            return promote()
        }
        select{
        case <-ctx.Done():return ctx.Err()
        case <-timer.C:
            return fmt.Errorf("remote M4 unproved: no authenticated reverse IPv4 or server M4 commit control before cold overlap deadline")
        case <-ticker.C:
        }
    }
}

func runClient(ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,coldReauth bool,
    connected *bool,ready ...chan<- struct{})error{
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
            if seg.Flags&(faketcp.FlagSYN|faketcp.FlagACK)==(faketcp.FlagSYN|faketcp.FlagACK){
                if !seg.MSSSet||seg.MSS<536||seg.MSS>1460{
                    select{case errs<-fmt.Errorf("invalid current V4 peer SYNACK MSS %d",seg.MSS):default:}
                    return
                }
                log.Printf("V4_PUBLIC_ACTUAL_PEER_SYNACK_MSS_V1 side=client peer_advertised_mss=%d",seg.MSS)
            }
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
    coldSynStart:=time.Now()
    if coldReauth{log.Printf("V4_PUBLIC_COLD_STAGE role=client stage=syn_start unix_ms=%d",coldSynStart.UnixMilli())}
    if err:=assoc.Start(coldSynStart);err!=nil{return err}
    dialCtx,cancel:=context.WithTimeout(ctx,20*time.Second)
    defer cancel()
    // A first SYN may precede server AF_PACKET bind just as a post-dead
    // SYN can. Drive the SAME original bounded FakeTCP RTO/MaxSYNRetries
    // at initial connect and cold reauth. Association freezes local MSS at
    // creation; retries cannot change SYN TCP options or skip TLS admission.
    err=waitForOriginalColdSYN(dialCtx,assoc)
    if err!=nil{return err}
    if coldReauth{log.Printf("V4_PUBLIC_COLD_STAGE role=client stage=syn_established unix_ms=%d elapsed_ms=%d",time.Now().UnixMilli(),time.Since(coldSynStart).Milliseconds())}
    var policy realityfront.AdmissionPolicy
    switch c.fecMode{
    case realityfront.FecV2Fixed:
        policy,err=realityfront.PolicyForClientWithInitialAndCipher(1,"fixed",4,4,20,c.recordCipher)
    case realityfront.FecV2Auto:
        policy,err=realityfront.PolicyForClientWithInitialAndCipher(1,"auto",0,4,20,c.recordCipher)
    default:
        policy,err=realityfront.PolicyForClientWithInitialAndCipher(1,"off",0,4,20,c.recordCipher)
    }
    if err!=nil{return err}
    applyLease:=configureAuthenticatedClientIPv4(tun)
    if c.leaseMustStay{
        // New owner must retain the same verified /32 until OLD native
        // Stop; server restart that issues another address must report a
        // real reconfiguration need instead of silently changing live TCP.
        applyLease=func(lease string)error{
            if tun.cidr!=lease{
                return fmt.Errorf("new path authenticated lease differs from active OS tunnel address")
            }
            return configureAuthenticatedClientIPv4(tun)(lease)
        }
    }
    native,err:=realityfront.NewV4LinuxClientProduct(
        realityfront.V4LinuxClientProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,SharedTun:c.sharedTun,
            CleanupOwnedNetwork:productNativeCleanup(c,tun),
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            ConfigureLeaseIPv4:applyLease,
            FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
        })
    if err!=nil{return err}
    cfg:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{ServerName:c.serverName,RouteKey:c.routeKey,VerifyServer:true,RootCAs:c.tlsRoots,Timeout:15*time.Second},
        Username:c.username,Password:c.password,TunnelID:c.tunnel[:],
        AutoLease:c.autoIP,InstallationID:c.installation[:],
        ClientLimit:c.recordLimit,DesiredLanes:1,LaneID:1,Policy:policy,
    }
    nativeAdmissionStart:=time.Now()
    stopColdRTO:=driveOriginalClientColdBootstrapRTO(dialCtx,assoc)
    _,err=native.ConnectAuthenticatedPeer(dialCtx,assoc,cfg)
    resent,retryErr:=stopColdRTO()
    if resent>0{
        log.Printf("V4_PUBLIC_FAKETCP_CLIENT_COLD_DATA_RTO role=client mode=%s actual_original_retransmissions=%d post_detach=0",
            c.fecMode,resent)
    }
    if err!=nil||retryErr!=nil{
        // Failed cold admission still owns a constructed native product.
        // It must release its loans/socket/generation before a new attempt.
        return errors.Join(err,retryErr,native.Close())
    }
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
    repeatOriginalDetachedTLSFinalACK(ctx,assoc)
    if c.rotationGeneration>1&&c.sharedTun!=nil{
        // The Rust candidate is ready to receive real M4 data but does
        // NOT own the default TUN route yet. The currently working A keeps
        // forwarding until native B proves the peer actually committed B.
        // A timeout closes only B and preserves A's exact old mapping.
        err=waitOriginalNativeM4PeerProof(ctx,native.OriginalLoopPulse,
            native.PromoteNormalAfterAuthenticatedPeerRx,5*time.Second)
        if err!=nil{
            log.Printf("V4_PUBLIC_NORMAL_REMOTE_M4_UNPROVEN role=client generation=%d client_port=%d old_tun_route_preserved=1",
                c.rotationGeneration,c.localPort)
            return errors.Join(err,native.Close())
        }
        log.Printf("V4_PUBLIC_NORMAL_REMOTE_M4_PROVEN role=client generation=%d client_port=%d native_authenticated_control_or_ipv4=1 tun_route_promoted=1",
            c.rotationGeneration,c.localPort)
    }
    if coldReauth{log.Printf("V4_PUBLIC_COLD_STAGE role=client stage=native_ready unix_ms=%d elapsed_ms=%d",time.Now().UnixMilli(),time.Since(nativeAdmissionStart).Milliseconds())}
    log.Printf("V4_PUBLIC_GO_RX_HANDOFF role=client mode=%s filtered=1 rust_ready=1 original_send_fd_open=1",c.fecMode)
    *connected=true
    log.Printf("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client Rust_owner=active real_raw_tun=1")
    if len(ready)>0&&ready[0]!=nil{
        // The only valid promotion point is after protected original TLS,
        // native Rust M4, DATA handoff filter and OS config/readback.
        select{case ready[0]<-struct{}{}:default:}
    }
    startV3ProductTimeline(ctx,"client",native.OriginalLoopPulse,native.OriginalOuterCounters)
    // Rust authenticates dead90. Observe one low-frequency terminal flag in
    // ALL Normal modes; neither ACK nor local driver errors may reauthorize TLS.
    err=monitorPublicNativePeer(ctx,errs,func()bool{return handoffCommitted.Load()},native.OriginalLoopPulse)
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
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,
    leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,
    coldReauth bool,connected *bool)(retErr error){
    if epochs==nil{return realityfront.ErrAdmissionParams}
    if leases!=nil||c.manualClientLease4.IsValid(){
        return runSharedMultiServer(ctx,c,ifindex,tun,raw,emit,leases,epochs,connected)
    }
    certificate,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    product,err:=realityfront.NewV4LinuxServerProduct(
        realityfront.V4LinuxServerProductConfig{
            Epochs:epochs,NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,
            CleanupOwnedNetwork:productNativeCleanup(c,tun),
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
            PeerPersona:c.peerPersona,Authenticate:originalV4CredentialCheck(c),
        })
    if err!=nil{return err}
    table,err:=faketcp.NewServerAssociationTable(32,emit)
    if err!=nil{return err}
    reply:=realityfront.ServerAdmissionConfig{
        TLS:realityfront.ServerConfig{ServerName:c.serverName,RouteKey:c.routeKey,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{certificate}},
            Timeout:15*time.Second},
        ExpectedUsername:c.username,ExpectedPassword:c.password,ServerLimit:c.recordLimit,
        AllocateLease:originalV4AutomaticLease(leases),
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            if len(req.TunnelID)!=16||req.DesiredLanes!=1||req.LaneID!=1{
                return realityfront.ErrAdmissionParams
            }
            if req.AutoLease{
                if leases==nil{return realityfront.ErrAdmissionParams}
            }else if c.tunnel==[16]byte{}||string(req.TunnelID)!=string(c.tunnel[:]){
                return realityfront.ErrAdmissionParams
            }
            return nil
        },
    }
    errs:=make(chan error,1)
    admitted:=make(chan struct{},1)
    var handoffCommitted atomic.Bool
    var goPostHandoffDataCopies atomic.Uint64
    var firstColdSYN atomic.Bool
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
                if !seg.MSSSet||seg.MSS<536||seg.MSS>1460{
                    select{case errs<-fmt.Errorf("invalid current V4 peer SYN MSS %d",seg.MSS):default:}
                    return
                }
                log.Printf("V4_PUBLIC_ACTUAL_PEER_SYN_MSS_V1 side=server peer_advertised_mss=%d",seg.MSS)
                if coldReauth&&firstColdSYN.CompareAndSwap(false,true){log.Printf("V4_PUBLIC_COLD_STAGE role=server stage=first_syn unix_ms=%d",time.Now().UnixMilli())}
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
                        nativeAcceptStart:=time.Now()
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
                        if coldReauth{log.Printf("V4_PUBLIC_COLD_STAGE role=server stage=native_ready unix_ms=%d elapsed_ms=%d",time.Now().UnixMilli(),time.Since(nativeAcceptStart).Milliseconds())}
                        log.Printf("V4_PUBLIC_GO_RX_HANDOFF role=server mode=%s filtered=1 rust_ready=1 original_send_fd_open=1",c.fecMode)
                        log.Printf("V4_ORIGINAL_GO_SERVER_NATIVE_READY role=server Rust_owner=active real_raw_tun=1")
                        startV3ProductTimeline(ctx,"server",product.OriginalLoopPulse,product.OriginalOuterCounters)
                    }()
                default:}
            }
        }
    }()
    err=monitorPublicNativePeer(ctx,errs,func()bool{return handoffCommitted.Load()},product.OriginalLoopPulse)
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


// PLAN028: one real Go FakeTCP server listening port, many independent
// credential-verified device sessions and ONE Rust-owned physical TUN reader.
// No Go steady-state plaintext/record loop is introduced here. Each admitted
// association owns its own original-Go TLS -> Rust AEAD/PN M1/M4 generation.
type originalV4MultiRecord struct {
    assoc *faketcp.ServerAssociation
    product *realityfront.V4LinuxServerProduct
    lease string // server verified protected TLS /32, never client claimed
    peer faketcp.DetachedPeer
    ready bool
    stopping bool
}
func runSharedMultiServer(
    ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,
    leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,
    connected *bool,
)(retErr error){
    if epochs==nil||connected==nil||
        (leases==nil&&!c.manualClientLease4.IsValid())||
        (leases!=nil&&c.manualClientLease4.IsValid()){
        return realityfront.ErrAdmissionParams
    }
    trustedManualLease:=""
    if c.manualClientLease4.IsValid(){trustedManualLease=c.manualClientLease4.String()}
    certificate,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    shared,err:=realityfront.NewV4LinuxSharedTun(tun.f,c.tunName)
    if err!=nil{return err}
    table,err:=faketcp.NewServerAssociationTable(32,emit)
    if err!=nil{
        _=shared.Close()
        return err
    }
    runCtx,cancel:=context.WithCancel(ctx)
    var mu sync.Mutex
    records:=make(map[*faketcp.ServerAssociation]*originalV4MultiRecord,32)
    detached:=make(map[*faketcp.ServerAssociation]faketcp.DetachedPeer,32)
    stopping:=false
    var admitted sync.WaitGroup
    var ever atomic.Bool
    transportErr:=make(chan error,1)
    // Original Go TLS protected credentials and automatic lease allocation
    // are shared policy, while each p has a different immutable cold epoch.
    reply:=realityfront.ServerAdmissionConfig{
        TLS:realityfront.ServerConfig{ServerName:c.serverName,RouteKey:c.routeKey,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{certificate}},
            Timeout:15*time.Second},
        ExpectedUsername:c.username,ExpectedPassword:c.password,
        ServerLimit:c.recordLimit,AllocateLease:originalV4AutomaticLease(leases),
        ValidateRequest:func(req realityfront.AdmissionRequest)error{
            if len(req.TunnelID)!=16||req.DesiredLanes!=1||req.LaneID!=1{
                return realityfront.ErrAdmissionParams
            }
            if leases!=nil{
                if !req.AutoLease{return realityfront.ErrAdmissionParams}
            }else if req.AutoLease||string(req.TunnelID)!=string(c.tunnel[:]){
                // Manual /32 is server-owned and tied to the exact
                // configured, TLS-authenticated tunnel ID.
                return realityfront.ErrAdmissionParams
            }
            return nil
        },
    }
    peersLocked:=func()[]faketcp.DetachedPeer{
        peers:=make([]faketcp.DetachedPeer,0,len(detached))
        for _,p:=range detached{peers=append(peers,p)}
        return peers
    }
    retire:=func(rec *originalV4MultiRecord,reason string)error{
        if rec==nil||rec.product==nil||!rec.ready{return nil}
        // Read the genuine per-owner Rust M2 effective state BEFORE Stop;
        // the shared manual server has no singleton process-wide counters.
        // This is cold Stop only, never a packet path and never CLI intent.
        outer,outerErr:=rec.product.OriginalOuterCounters()
        // Read the REAL per-session Rust FEC applied strength before
        // generation-owned Stop; not the server's global CLI default.
        if effective,e:=rec.product.OriginalFECReadback();e==nil{
            log.Printf("V4_PUBLIC_MULTI_NATIVE_FEC_EFFECTIVE role=server mode=%s profile=%d requested=%d applied=%d pending=%t",
                effective.Mode,effective.Profile,effective.RequestedRevision,effective.AppliedRevision,effective.Pending)
        }
        if err:=rec.product.Close();err!=nil{
            return fmt.Errorf("PLAN028 Rust native per-session Stop %s: %w",reason,err)
        }
        mu.Lock()
        delete(detached,rec.assoc)
        delete(records,rec.assoc)
        peers:=peersLocked()
        var filterErr error
        // If zero routes remain, the previous exclusion safely continues to
        // drop retired DATA, while a new SYN is always still eligible.
        if len(peers)>0{filterErr=raw.ExcludeDetachedDataSet(peers)}
        mu.Unlock()
        table.Remove(rec.assoc.Flow())
        if filterErr!=nil{return filterErr}
        logAuthenticOuter("server",outer,outerErr)
        log.Printf("V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=%s remaining=%d",
            reason,len(peers))
        if outerErr!=nil{
            return fmt.Errorf("PLAN028 authenticated per-session Rust outer-repair readback %s: %w",reason,outerErr)
        }
        return nil
    }
    // Close in the invariant order: deny NEW Go admissions, join cold TLS
    // admission goroutines, Stop every committed Rust generation, THEN join
    // the independent native TUN reader; never release the OS TUN first.
    defer func(){
        cancel()
        mu.Lock();stopping=true;mu.Unlock()
        admitted.Wait()
        mu.Lock()
        active:=make([]*originalV4MultiRecord,0,len(records))
        for _,rec:=range records{if rec.ready{active=append(active,rec)}}
        mu.Unlock()
        for _,rec:=range active{
            if err:=retire(rec,"server-close");err!=nil{
                retErr=errors.Join(retErr,err)
            }
        }
        table.Close()
        if err:=shared.Close();err!=nil{
            retErr=errors.Join(retErr,err)
            log.Printf("V4_PUBLIC_SHARED_TUN_STOP_INCOMPLETE error=%v",err)
        }else{
            log.Printf("V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server")
        }
        *connected=ever.Load()
    }()
    accept:=func(rec *originalV4MultiRecord){
        defer admitted.Done()
        published:=false
        defer func(){
            if !published{
                mu.Lock()
                if !rec.ready{delete(records,rec.assoc)}
                mu.Unlock()
                table.Remove(rec.assoc.Flow())
            }
        }()
        cfg:=realityfront.V4LinuxServerProductConfig{
            Epochs:epochs,NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,SharedTun:shared,
            // Only real authenticated auto-lease server sessions reach
            // this path; old manual/standalone duplicate lane stays DENY.
            AllowLaneReplacement:true,
            ManualLease4:trustedManualLease,
            CleanupOwnedNetwork:productNativeCleanup(c,tun),
            // One authenticated peer cannot mutate a sibling's TUN MTU.
            // The original Rust per-session record/route budgets still apply.
            ConfigureTunnelMTU:nil,
            FECMode:c.fecMode,FECProfile:c.fecProfile,
            // The original TLS policy is this client's owner configuration;
            // server process --mode is not a global FEC admission filter.
            PerClientNormalFEC:true,
            DisableOuterRepair:c.disableOuterRepair,PeerPersona:c.peerPersona,
            Authenticate:originalV4CredentialCheck(c),
        }
        p,err:=realityfront.NewV4LinuxServerProduct(cfg)
        if err!=nil{
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=product")
            return
        }
        mu.Lock();rec.product=p;mu.Unlock()
        sess,err:=p.AcceptAuthenticatedPeer(runCtx,rec.assoc,reply)
        if err!=nil{
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=original_tls_or_owner")
            return
        }
        lease,err:=sess.AuthenticatedLeaseIPv4()
        if err!=nil||lease==""{
            _=p.Close()
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=verified_lease")
            return
        }
        state,exists:=rec.assoc.TransitionState()
        flow:=rec.assoc.Flow()
        if !exists||state!=faketcp.TransitionDetached||
           flow.ServerIP!=c.localIP.As4()||flow.ServerPort!=c.localPort{
            _=p.Close()
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=detached_scope")
            return
        }
        peer:=faketcp.DetachedPeer{IP:flow.ClientIP,Port:flow.ClientPort}
        mu.Lock()
        if stopping||runCtx.Err()!=nil{
            mu.Unlock()
            _=p.Close()
            return
        }
        detached[rec.assoc]=peer
        if err=raw.ExcludeDetachedDataSet(peersLocked());err!=nil{
            delete(detached,rec.assoc)
            mu.Unlock()
            _=p.Close()
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=kernel_filter")
            return
        }
        rec.lease=lease
        rec.peer=peer
        rec.ready=true
        published=true
        older:=make([]*originalV4MultiRecord,0,1)
        for _,sibling:=range records{
            if sibling!=rec&&sibling.ready&&!sibling.stopping&&
               sibling.lease==lease{
                // New original-TLS generation already published its native
                // TUN /32 route and fenced the old generation. Retire only
                // THAT old identity, never another device under same account.
                sibling.stopping=true
                older=append(older,sibling)
            }
        }
        count:=len(detached)
        mu.Unlock()
        ever.Store(true)
        autoLease:=0
        if leases!=nil{autoLease=1}
        log.Printf("V4_PUBLIC_MULTI_SESSION_READY role=server one_port=%d active_detached_flows=%d auto_lease=%d original_TLS=1 Rust_M4=1",
            c.localPort,count,autoLease)
        for _,old:=range older{
            if err:=retire(old,"same-lease-new-generation");err!=nil{
                select{case transportErr<-err:default:}
                return
            }
        }
    }
    // 32 is the FakeTCP *cold association* table, not the number of
    // authenticated Rust native owners. prepare_side has MAX_SESSIONS=16.
    // Truthful readiness avoids advertising unqualified 32-live capacity.
    log.Printf("V4_PUBLIC_MULTI_SERVER_READY role=server port=%d cold_association_slots=32 native_owner_slots=16 shared_rust_tun=1",
        c.localPort)
    go func(){
        for {
            seg,_,readErr:=raw.ReadSegment()
            if readErr!=nil{
                if runCtx.Err()!=nil{return}
                select{case transportErr<-readErr:default:}
                return
            }
            if seg.DstPort!=c.localPort{continue}
            if faketcp.IsInitialSYN(seg){
                if !seg.MSSSet||seg.MSS<536||seg.MSS>1460{continue}
                isn,e:=originalRandomISN()
                if e!=nil{
                    select{case transportErr<-e:default:}
                    return
                }
                assoc,e:=table.AddSYN(seg,isn,time.Second)
                if errors.Is(e,faketcp.ErrAssociationExists){continue}
                if e!=nil{
                    // One untrusted new SYN cannot evict a live authenticated
                    // generation. Table capacity is bounded and swept.
                    continue
                }
                synack,e:=assoc.SYNACKSegment()
                if e==nil{e=emit(synack)}
                if e!=nil{
                    select{case transportErr<-e:default:}
                    return
                }
                continue
            }
            assoc,ok:=table.GetSegment(seg)
            if !ok||assoc.State()==faketcp.ServerAssociationClosed{continue}
            if state,exists:=assoc.TransitionState();exists&&
               state==faketcp.TransitionDetached{
                // The kernel socket filter already excludes authenticated
                // DATA from Go; ACK, FIN, and new SYN are still visible.
                continue
            }
            outcome,e:=assoc.HandleSegment(seg,time.Now())
            if e!=nil{
                if !errors.Is(e,faketcp.ErrHandshakeState){
                    log.Printf("V4_PUBLIC_MULTI_COLD_SEGMENT_REJECT")
                }
                continue
            }
            if outcome.AckNeeded{
                if e=emit(assoc.ACKSegment(outcome.Ack));e!=nil{
                    select{case transportErr<-e:default:}
                    return
                }
            }
            if assoc.State()!=faketcp.ServerAssociationEstablished{continue}
            mu.Lock()
            if !stopping{
                if _,exists:=records[assoc];!exists{
                    rec:=&originalV4MultiRecord{assoc:assoc}
                    records[assoc]=rec
                    admitted.Add(1)
                    go accept(rec)
                }
            }
            mu.Unlock()
        }
    }()
    ticker:=time.NewTicker(time.Second)
    defer ticker.Stop()
    for {
        select{
        case <-runCtx.Done():
            return nil
        case e:=<-transportErr:
            return e
        case <-ticker.C:
            now:=time.Now()
            table.Sweep(now)
            if e:=table.EmitRetransmitDue(now);e!=nil{
                return e
            }
            mu.Lock()
            living:=make([]*originalV4MultiRecord,0,len(records))
            for _,rec:=range records{
                if rec.ready&&!rec.stopping{living=append(living,rec)}
            }
            mu.Unlock()
            for _,rec:=range living{
                pulse,e:=rec.product.OriginalLoopPulse()
                if e!=nil{continue}
                if !publicNativeHealthDead(pulse){continue}
                mu.Lock()
                if rec.stopping{mu.Unlock();continue}
                rec.stopping=true
                mu.Unlock()
                if e:=retire(rec,"authenticated-health90");e!=nil{
                    return e
                }
            }
        }
    }
}
