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
    "runtime"
    "os/signal"
    "strconv"
    "strings"
    "sync"
    "sync/atomic"
    "syscall"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/v4productcli/dnsnative"
    "github.com/lly8666/wobuzhidao/internal/v4productcli/rstguard"
    "github.com/lly8666/wobuzhidao/internal/v4productcli/rootjournal"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
    "github.com/lly8666/wobuzhidao/internal/v4routekey"
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
    peerHost string // Android Root DNS A bootstrap before real FakeTCP SYN
    localPort uint16
    peerPort uint16
    tunName string
    tunCIDR string
    serverName string
    decoyTarget string // server-only fixed ordinary-TLS target
    routeKey []byte
    tlsRoots *x509.CertPool
    tlsVerifyServer bool // client-only: default OFF (insecure legacy compatibility)
    tlsCert string
    tlsKey string
    username string
    password string
    users map[string]string
    manualClientLeases4 map[string]string // authenticated account -> server-owned unique /32
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
    startupPaddingMode uint8 // client V2 Normal/FEC/Game cold: 0 off, 1 TLS, 2 flows; server CLI not authority
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
    androidNetworkHandle uint64 // selected physical ConnectivityManager Network
    androidClatParent,androidClatPrefix string // existing Android 464XLAT underlay
    androidPhysicalMTU uint32 // same interface cold readback
    androidRouteUID int // legacy single ordinary App UID; never root/global
    androidRouteUIDs []int // canonical 2..16 ordinary Android App UIDs, cold-only
    androidRouteAllApps bool // ordinary app UID ranges, no root/system/main FIB
    androidRouteExcludeAppIDs []int // own + KernelSU manager per-user app ID exclusions
    androidDirectCIDRs []string // opt-in real kernel throw routes in SAME UID table
    androidCNIPv4Snapshot string // signed allocation snapshot, cold-only
    // Cold-authorized original M4 TUN UDP/53 rewrite to 1.1.1.1 only.
    // System resolver/netd and CN physical split are NOT enabled by this.
    androidTunnelDNS bool
    androidTunnelDNSUpstream netip.Addr
    androidAppTCPDNS bool // explicit kernel App TCP53 DNS listener
    androidSystemDNS bool // selected UID + selected netId plaintext IPv4 DNS
    androidSystemDNS6 bool // optional IPv6 destination plaintext DNS
    androidIPv6Gateway string // explicitly provisioned server TUN IPv4 for SIT carrier
    androidIPv6DirectCIDRs []string
    androidIPv6DirectLAN bool
    serverIPv6Carrier bool // Linux server kernel 6rd/SIT, default off
    androidTetherInterface,androidTetherSubnet string
    androidTetherIfindex int
    // Explicit TUN-App UDP53 physical 223.5.5.5 compatibility mode.
    androidPhysicalDNS bool
    androidPhysicalDNSUpstream netip.Addr // original Rust M4 real bound UDP53 upstream
    androidNativeHealthSeconds uint32 // B37 cold Rust HealthClock interval, no Go packet or heartbeat worker
    // Original pinned CN8503 QNAME classification in Rust M4, opt-in.
    androidCNDNSSplit bool
    // Signed APK's verified offline CN list only, not live DNS capture.
    androidCNSnapshot *dnsnative.CNRules
    // Constructed from selected kernel interface and Android Network netId
    // before protected TLS. No socket is opened and no DNS request occurs
    // until the future Rust/TUN DNS packet owner is independently qualified.
    androidPhysicalDNSDial dnsnative.DialFunc
    // Process-scoped original Rust TUN reader. Never included in config
    // wire/user arguments; only initialized by genuine cold OS Go owner.
    sharedTun *realityfront.V4LinuxSharedTun
    // Transient generation safety: a pending new-path TLS session cannot
    // mutate an active generation's authenticated inner IPv4 address.
    leaseMustStay bool
    tunFqMaxrateMbps int
    tunTxQLenPackets int
}
// Cold default uses a contiguous pool wholly within the owned TUN, disjoint
// from server and explicitly reserved static /32 addresses. LeaseRegistry
// remains sole owner of 7-day device lease allocation, renewal and expiry.
func defaultV4ServerLeasePool(tun netip.Prefix,statics map[string]string)(netip.Prefix,error){
 if !tun.IsValid()||!tun.Addr().Is4()||tun.Bits()>29{return netip.Prefix{},fmt.Errorf("server TUN too small for disjoint automatic IPv4 pool")}
 lo:=uint64(binary.BigEndian.Uint32(tun.Masked().Addr().AsSlice()))
 end:=lo+(uint64(1)<<uint(32-tun.Bits()))
 blocked:=[]uint64{uint64(binary.BigEndian.Uint32(tun.Addr().AsSlice()))}
 for _,v:=range statics{
  fixed,e:=netip.ParsePrefix(v)
  if e!=nil||!fixed.Addr().Is4()||fixed.Bits()!=32{return netip.Prefix{},fmt.Errorf("invalid fixed /32")}
  blocked=append(blocked,uint64(binary.BigEndian.Uint32(fixed.Addr().AsSlice())))
 }
 bits:=24
 if tun.Bits()>=bits{bits=tun.Bits()+1}
 for ;bits<=30;bits++{
  size:=uint64(1)<<uint(32-bits)
  for i:=uint64(0);i<4096&&size*(i+1)<=end-lo;i++{
   at:=end-size*(i+1);free:=true
   for _,v:=range blocked{if v>=at&&v<at+size{free=false;break}}
   if !free{continue}
   var raw [4]byte
   binary.BigEndian.PutUint32(raw[:],uint32(at))
   return netip.PrefixFrom(netip.AddrFrom4(raw),bits),nil
  }
 }
 return netip.Prefix{},fmt.Errorf("no disjoint automatic IPv4 pool within server TUN")
}

// This SYN presentation was observed by the original FakeTCP association,
// not supplied by credentials. Use it ONLY after protected TLS authenticates
// the lane; never turn an untrusted pre-TLS hint into account authority.
// Shared Normal and Game owners must not all inherit the Windows CLI fallback.
func originalV4ColdAssocPeerPersona(assoc *faketcp.ServerAssociation,
 fallback realityfront.V4PublicNativePeerPersona,
)(realityfront.V4PublicNativePeerPersona,bool){
 if assoc==nil{return fallback,false}
 profile:=assoc.PeerTCPProfile()
 if !profile.OriginalSYNPersonaKnown{return fallback,false}
 if profile.OriginalSYNPersona==faketcp.PacketPersonaWindows11{
  return realityfront.V4PeerWindows11,true
 }
 return realityfront.V4PeerLegacy,true
}

// Read a bounded, deterministic set of ordinary app UIDs. The caller's
// PackageManager must authenticate each package->UID association first;
// Go validates the kernel-safe numeric and canonical group boundary.
func parseAndroidRouteGroupArg(s string)([]int,error){
    if s==""{return nil,nil}
    parts:=strings.Split(s,",")
    if len(parts)<2||len(parts)>16{
        return nil,fmt.Errorf("Android UID group needs 2..16 entries")
    }
    uids:=make([]int,0,len(parts))
    previous:=0
    for _,p:=range parts{
        if p==""||strings.TrimSpace(p)!=p{
            return nil,fmt.Errorf("Android UID group has empty/spaced entry")
        }
        uid,err:=strconv.Atoi(p)
        if err!=nil||uid<10000||uid>1999999||uid<=previous{
            return nil,fmt.Errorf("Android UID group must be unique, sorted, ordinary app UIDs")
        }
        previous=uid
        uids=append(uids,uid)
    }
    return uids,nil
}
// Canonical per-user application IDs, never arbitrary system/root UID ranges.
func parseAndroidExcludedAppIDsArg(text string)([]int,error){
    if text==""{return nil,fmt.Errorf("all-app routing needs owner+root-manager exclusions")}
    parts:=strings.Split(text,",")
    if len(parts)<2||len(parts)>8{return nil,fmt.Errorf("bounded exclusions require 2..8 app IDs")}
    result:=make([]int,0,len(parts))
    previous:=0
    for _,token:=range parts{
        if token==""||strings.TrimSpace(token)!=token{
            return nil,fmt.Errorf("invalid excluded app ID token")
        }
        v,e:=strconv.Atoi(token)
        if e!=nil||v<10000||v>19999||v<=previous{
            return nil,fmt.Errorf("excluded app IDs must be unique sorted 10000..19999")
        }
        result=append(result,v);previous=v
    }
    return result,nil
}

func parse(role string,args []string)(config,error){
    var c config
    c.role=role
    if role!="client"&&role!="server"{return c,fmt.Errorf("unknown role")}
    flags:=flag.NewFlagSet("wbd-v4-"+role,flag.ContinueOnError)
    iface:=flags.String("raw-interface","","real physical underlay interface")
    androidNet:=flags.Uint64("android-network-handle",0,"Android client-only Network.getNetworkHandle() (mandatory; cold per-socket binding)")
    androidRouteUID:=flags.Int("android-route-uid",0,
        "Android ARM64 Root ONLY: one app UID (>=10000) routed after original TLS/lease/M4, 0 disables routing")
    androidRouteGroup:=flags.String("android-route-uids","",
        "Android Root: canonical 2..16 ordinary App UIDs; mutually exclusive with single and all-apps")
    androidRouteAll:=flags.Bool("android-route-all-apps",false,
        "Android Root after authenticated lease/M4: route ordinary App UIDs in 20 profiles, never system/root")
    androidRouteExclude:=flags.String("android-route-exclude-appids","",
        "Android all-apps: mandatory canonical excluded controller+root-manager app IDs (10000..19999)")
    androidDirectCIDRs:=flags.String("android-direct-cidrs","",
        "Android Root: up to sixteen explicit IPv4 CIDRs to bypass the WBD private UID table; empty keeps original full tunnel")
    cnIPv4File:=flags.String("android-cn-ipv4-file","","Android Root: signed APNIC CN IPv4 prefixes for ordinary business direct routing")
    cnGeositeFile:=flags.String("android-cn-geosite-file","",
        "Android Root cold source-lock: APK verified owner-only CN8503 file (not DNS interception)")
    androidTunnelDNS:=flags.Bool("android-tunnel-dns",false,
        "Android Root: after real protected TLS/lease and Rust M4, redirect captured ordinary App UDP/53 via authenticated 1.1.1.1 tunnel; not system Resolver or CN split")
    androidPhysicalDNS:=flags.Bool("android-physical-dns",false,
        "Android Root optional: ordinary captured App TUN UDP/53 to physical 223.5.5.5; takes priority over tunnel DNS, not CN split/system Resolver")
    androidAppTCPDNS:=flags.Bool("android-app-tcp-dns",false,
        "Android Root: optional ordinary App TCP53 follows the selected DNS mode through kernel TCP")
    androidClatParent:=flags.String("android-clat-parent","","Android Root: existing CLAT IPv6 parent interface")
    androidClatPrefix:=flags.String("android-clat-prefix","","Android Root: selected Network NAT64 /96")
    androidIPv6Gateway:=flags.String("android-ipv6-gateway","","Android Root: opt-in IPv6-in-IPv4, provisioned WBD server TUN private IPv4")
    androidIPv6DirectCIDRs:=flags.String("android-ipv6-direct-cidrs","","Android Root: comma-separated IPv6 direct CIDRs within IPv6 carrier")
    androidIPv6DirectLAN:=flags.Bool("android-ipv6-direct-lan",false,"Android Root: direct selected physical Network IPv6 on-link prefixes")
    serverIPv6Carrier:=flags.Bool("inner-ipv6",false,"Linux server: opt-in kernel SIT/6rd IPv6 business over authenticated IPv4; requires IPv6 forwarding and egress")
    androidSystemDNS6:=flags.Bool("android-system-dns6",false,
        "Android Root: additionally capture selected Network/UID IPv6 UDP/TCP53 to existing DNS owner")
    androidSystemDNS:=flags.Bool("android-system-dns",false,
        "Android Root: selected UID and selected Network ordinary IPv4 UDP/TCP53 system DNS (no Private DNS/DoH)")
    tetherInterface:=flags.String("android-tether-interface","","Android Root: explicitly selected existing software tether interface")
    tetherSubnet:=flags.String("android-tether-subnet","","Android Root: exact active downstream IPv4 subnet")
    tetherIndex:=flags.Int("android-tether-ifindex",0,"Android Root: exact downstream ifindex")
    androidNativeHealth:=flags.Uint("android-native-health-seconds",15,
         "Android Root: actual Rust authenticated native Health interval 15 or 30 seconds, 90s dead unchanged")
    androidTunnelDNSUpstream:=flags.String("android-tunnel-dns-upstream-ipv4","1.1.1.1","Android Root: tunnel IPv4 DNS upstream for all original modes")
    androidPhysicalDNSUpstream:=flags.String("android-physical-dns-upstream-ipv4","223.5.5.5",
        "Android Root: selected-Network physical DNS IPv4 for captured App UDP/53 and original Go peer-host cold UDP/TCP53 bootstrap; default 223.5.5.5; not system Resolver")
    androidCNDNSSplit:=flags.Bool("android-cn-dns-split",false,
        "Android Root optional: match original App UDP53 QNAME against pinned CN8503; CN via physical 223.5.5.5, other names via WBD tunnel 1.1.1.1")
    ip:=flags.String("local-ip","","underlay local IPv4; server may omit or use 0.0.0.0 to resolve unique IPv4 of --raw-interface (NAT-friendly)")
    peer:=flags.String("peer-ip","","remote underlay IPv4 (client only)")
    peerHost:=flags.String("peer-host","","Android Root client only: physical 223.5.5.5 DNS server name bootstrap before FakeTCP SYN")
    defaultPort:=uint(0)
    if role=="server"{defaultPort=443}
    port:=flags.Uint("local-port",defaultPort,"original FakeTCP local port (server default 443)")
    remotePort:=flags.Uint("peer-port",0,"remote FakeTCP port (client)")
    tunName:=flags.String("tun-name","wbdv40","owned original Linux TUN name")
    defaultTun:=""
    if role=="server"{defaultTun="10.66.0.1/24"}
    tunCIDR:=flags.String("tun-ipv4",defaultTun,"owned real TUN IPv4 CIDR (server default 10.66.0.1/24)")
    name:=flags.String("server-name","","original TLS recognized SNI")
    decoy:=flags.String("decoy","","server-only ordinary TLS target host:port; per-visitor random 15..45s cutoff, max8 concurrent splices")
    route:=flags.String("route-key-hex","","legacy/expert pre-shared 32-byte route key hex (64 characters)")
    routeShort:=flags.String("route-key","","8..32 ASCII letters/digits; v2 4096-iteration mobile-friendly PBKDF2 once then persistent 32B cache (prefer 24..32 random)")
    routeShortFile:=flags.String("route-key-file","","owner-only file with 8..32 short route-key; avoids argv disclosure")
    routeCache:=flags.String("route-key-cache-file","","persistent owner-only derived key cache; default user config directory")
    caPEM:=flags.String("tls-ca-pem","","client application-scoped trusted server CA/certificate PEM (used with TLS verification)")
    verifyTLS:=flags.Bool("tls-verify-server",false,"verify TLS certificate chain and server-name; default false (insecure legacy compatibility)")
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
    manualLeasesFile:=flags.String("manual-client-leases-file","","server mode-0600 JSON username->unique /32 bound only after protected auth")
    defaultMode:="normal"
    if role=="server"{defaultMode="shared"}
    mode:=flags.String("mode",defaultMode,"normal, fec-fixed, fec-auto, game2, game4; server defaults shared")
    peerPersona:=flags.String("peer-persona","legacy","expected original Go TLS peer envelope: legacy or windows11 (server-only)")
    profile:=flags.Uint("fec-profile",1,"FEC2 profile 0..6 for normal fixed; auto uses strong startup")
    cipherName:=flags.String("record-cipher","chacha20-poly1305","client authenticated V4 record AEAD: chacha20-poly1305, aes-128-gcm or aes-256-gcm")
    gameFec:=flags.String("game-fec","off","Game2/4 inner fixed FEC: off or fixed0..fixed6; BOTH authenticated endpoints must match; no Game Auto")
    startupPadding:=flags.String("startup-padding","off","Client requests off|tls|flows inside protected TLS admission; server follows verified per-session choice; fixed parity never padded")
    game4Copy:=flags.String("game4-copy-schedule","","Game4 default stagger-4-50-140; explicit stagger-4-20-60 legacy fallback or immediate rollback; Game2 unchanged")
    outerDefault:="on"
    if runtime.GOOS=="android"{outerDefault="off"}
    outerRepair:=flags.String("outer-repair",outerDefault,
        "outer DATA retransmission on|off; Android ARM64 Normal/off first-connect supports off only")
    outerMTU:=flags.Int("outer-mtu",1460,"outer complete IPv4 IP-packet MTU in bytes (576..1500, no L2); inner TUN MTU automatic/read-only")
    rotateInterval:=flags.Duration("rotation-interval",0,"client: cold authenticated lane/group rotation on unchanged physical network (e.g. 5m); 0 disables")
    rotateJitter:=flags.Duration("rotation-jitter",0,"client: bounded random ±jitter for each rotation (e.g. 3s with --rotation-interval 18s); 0 preserves exact interval")
    tunFqDefault:=600
    if runtime.GOOS=="android"{tunFqDefault=0}
    tunFqRate:=flags.Int("tun-fq-maxrate-mbps",tunFqDefault,
        "owned Linux TUN fq 600Mbps (Android default 0: cannot assume tc or qdisc support)")
    tunTxQLen:=flags.Int("tun-txqlen-packets",2048,"owned original Linux TUN TX queue: 2048 bounded default, 500 explicit rollback")
    if err:=flags.Parse(args);err!=nil{return c,err}
    if runtime.GOOS=="android"{
        if role!="client"||*androidNet==0{
            return c,fmt.Errorf("Android root client needs explicit physical Network handle")
        }
        if *androidNativeHealth!=15&&*androidNativeHealth!=30{
            return c,fmt.Errorf("Android original Rust Health interval must be 15 or 30 seconds")
        }
        c.androidNativeHealthSeconds=uint32(*androidNativeHealth)
        if *peerHost!=""&&*peer!=""{
            return c,fmt.Errorf("Android peer-host and peer-ip are mutually exclusive")
        }
        if *androidRouteUID!=0&&(*androidRouteUID<10000||*androidRouteUID>1999999){
            return c,fmt.Errorf("Android route UID must identify one non-system application")
        }
        if *androidRouteUID!=0&&*androidRouteGroup!=""{
            return c,fmt.Errorf("Android single and group UID route flags are mutually exclusive")
        }
        if *androidRouteAll&&(*androidRouteUID!=0||*androidRouteGroup!=""){
            return c,fmt.Errorf("Android all-app and selected-app routing are mutually exclusive")
        }
        if !*androidRouteAll&&*androidRouteExclude!=""{
            return c,fmt.Errorf("Android exclude IDs require all-app mode")
        }
        if (*androidTunnelDNS||*androidPhysicalDNS||*androidCNDNSSplit)&&!*androidRouteAll&&*androidRouteUID==0&&
           *androidRouteGroup==""{
            return c,fmt.Errorf("Android tunnel DNS needs a selected ordinary App UID route")
        }
        // Physical explicitly selected takes precedence; legacy tunnel default unchanged.
        c.androidTunnelDNS=*androidTunnelDNS&&!*androidPhysicalDNS&&!*androidCNDNSSplit
        c.androidPhysicalDNS=*androidPhysicalDNS&&!*androidCNDNSSplit
        c.androidCNDNSSplit=*androidCNDNSSplit
        c.androidClatParent,c.androidClatPrefix=*androidClatParent,*androidClatPrefix
        if *androidIPv6Gateway!=""{
            gateway,e:=netip.ParseAddr(*androidIPv6Gateway)
            if e!=nil||!gateway.Is4()||!gateway.IsPrivate()||(!*androidRouteAll&&*androidRouteUID==0&&*androidRouteGroup==""){
                return c,fmt.Errorf("IPv6 carrier needs private server TUN IPv4 and selected App route scope")
            }
            c.androidIPv6Gateway=gateway.String()
        }
        if *androidIPv6DirectCIDRs!=""||*androidIPv6DirectLAN{
            if c.androidIPv6Gateway==""{return c,fmt.Errorf("IPv6 direct routes require IPv6 carrier")}
            var e error
            c.androidIPv6DirectCIDRs,e=rootjournal.ParseIPv6DirectCIDRs(*androidIPv6DirectCIDRs)
            if e!=nil{return c,e}
            c.androidIPv6DirectLAN=*androidIPv6DirectLAN
        }
        c.androidSystemDNS6=*androidSystemDNS6
        c.androidSystemDNS=*androidSystemDNS||c.androidSystemDNS6
        c.androidAppTCPDNS=*androidAppTCPDNS||c.androidSystemDNS
        if *tetherInterface!=""||*tetherSubnet!=""||*tetherIndex!=0{
            subnet,e:=netip.ParsePrefix(*tetherSubnet)
            if *tetherInterface==""||*tetherIndex<=0||e!=nil||!subnet.Addr().Is4()||
               !subnet.Addr().IsPrivate()||subnet!=subnet.Masked()||subnet.Bits()<8||subnet.Bits()>30||
               (!*androidRouteAll&&*androidRouteUID==0&&*androidRouteGroup==""){
                return c,fmt.Errorf("Android tether needs exact downstream and original App route scope")
            }
            c.androidTetherInterface,c.androidTetherSubnet,c.androidTetherIfindex=*tetherInterface,*tetherSubnet,*tetherIndex
        }
        if c.androidAppTCPDNS&&!c.androidTunnelDNS&&!c.androidPhysicalDNS&&!c.androidCNDNSSplit{
            return c,fmt.Errorf("App TCP DNS requires one selected DNS mode")
        }
        var e error
        c.androidTunnelDNSUpstream,e=dnsnative.ParsePhysicalDNSUpstreamIPv4(*androidTunnelDNSUpstream)
        if e!=nil{return c,fmt.Errorf("Android tunnel DNS upstream rejected: %w",e)}
        c.androidPhysicalDNSUpstream,e=dnsnative.ParsePhysicalDNSUpstreamIPv4(*androidPhysicalDNSUpstream)
        if e!=nil{return c,fmt.Errorf("Android physical DNS upstream rejected: %w",e)}
        if *androidPhysicalDNSUpstream!="223.5.5.5"&&
           !c.androidPhysicalDNS&&!c.androidCNDNSSplit&&*peerHost==""{
            return c,fmt.Errorf("custom physical DNS requires physical/CN-split App DNS or server peer-host bootstrap")
        }
        c.androidRouteUIDs,e=parseAndroidRouteGroupArg(*androidRouteGroup)
        if e!=nil{return c,e}
        c.androidDirectCIDRs,e=rootjournal.ParseDirectCIDRs(*androidDirectCIDRs)
        if e!=nil{return c,fmt.Errorf("Android cold direct IPv4 CIDRs rejected: %w",e)}
        if (len(c.androidDirectCIDRs)>0||*cnIPv4File!="")&&!(*androidRouteAll||*androidRouteUID!=0||*androidRouteGroup!=""){
            return c,fmt.Errorf("Android direct IPv4 CIDRs need selected or all-App UID scope")
        }
        if *androidRouteAll{
            c.androidRouteExcludeAppIDs,e=parseAndroidExcludedAppIDsArg(*androidRouteExclude)
            if e!=nil{return c,e}
            c.androidRouteAllApps=true
        }
        if *cnIPv4File!=""{
            data,err:=os.ReadFile(*cnIPv4File)
            if err!=nil{return c,err}
            if _,err=rootjournal.MergeCountryDirectCIDRs(nil,string(data),"");err!=nil{return c,err}
            c.androidCNIPv4Snapshot=string(data)
        }
        if *cnGeositeFile!=""{
            c.androidCNSnapshot,e=dnsnative.ReadPinnedCNFile(*cnGeositeFile)
            if e!=nil{
                return c,fmt.Errorf("signed Android CN8503 cold source rejected: %w",e)
            }
        }
        if c.androidCNDNSSplit&&c.androidCNSnapshot==nil{
            return c,fmt.Errorf("Android CN DNS split requires the original pinned geosite file")
        }
    }else if *androidNet!=0||*androidRouteUID!=0||
             *androidRouteGroup!=""||*androidRouteAll||*androidRouteExclude!=""||
              *androidDirectCIDRs!=""||*cnIPv4File!=""||*cnGeositeFile!=""||*peerHost!=""||
              *androidPhysicalDNSUpstream!="223.5.5.5"||*androidTunnelDNSUpstream!="1.1.1.1"||
              *androidTunnelDNS||*androidPhysicalDNS||*androidCNDNSSplit||*androidAppTCPDNS||*androidSystemDNS||*androidSystemDNS6||*androidIPv6Gateway!=""||*androidIPv6DirectCIDRs!=""||*androidIPv6DirectLAN||*androidClatParent!=""||*androidClatPrefix!=""||*tetherInterface!=""||*tetherSubnet!=""||*tetherIndex!=0{
        return c,fmt.Errorf("Android Network/routing parameters are Android-only")
    }
    if *serverIPv6Carrier&&(role!="server"||runtime.GOOS=="android"){
        return c,fmt.Errorf("inner-ipv6 is Linux server-only; use explicit Android gateway on client")
    }
    c.serverIPv6Carrier=*serverIPv6Carrier
    c.androidNetworkHandle=*androidNet
    c.androidRouteUID=*androidRouteUID
    modeGiven,autoGiven:=false,false
    flags.Visit(func(f *flag.Flag){if f.Name=="mode"{modeGiven=true};if f.Name=="auto-ip"{autoGiven=true}})
    if role=="server"&&*manualLease!=""&&!modeGiven{*mode="normal"}
    if role=="client"&&*tunCIDR==""&&*tunnel==""&&!autoGiven{*autoIP=true}
    if *passFile!="" {
        if *pass!="" {return c,fmt.Errorf("password and password-file are mutually exclusive")}
        value,e:=readPrivateArgFile(*passFile)
        if e!=nil{return c,fmt.Errorf("invalid password-file: %w",e)}
        *pass=value
    }
    if *routeShortFile!="" {
        if *routeShort!="" {return c,fmt.Errorf("route-key and route-key-file are mutually exclusive")}
        short,e:=readPrivateArgFile(*routeShortFile)
        if e!=nil{return c,fmt.Errorf("invalid route-key-file: %w",e)}
        *routeShort=short
    }
    if *routeFile!="" {
        if *route!=""||*routeShort!="" {return c,fmt.Errorf("route-key, route-key-hex and route-key-hex-file are mutually exclusive")}
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
    if *manualLeasesFile!=""{
        if role!="server"||*manualLease!=""||*usersFile==""{
            return c,fmt.Errorf("manual-client-leases-file requires users-file, not singleton lease")
        }
        raw,e:=readPrivateArgFile(*manualLeasesFile)
        if e!=nil{return c,fmt.Errorf("manual-client-leases-file: %w",e)}
        if e=json.Unmarshal([]byte(raw),&c.manualClientLeases4);e!=nil||
            len(c.manualClientLeases4)==0||len(c.manualClientLeases4)>len(c.users){
            return c,fmt.Errorf("manual-client-leases-file must be a nonempty authenticated-user subset")
        }
        seen:=make(map[netip.Addr]bool,len(c.manualClientLeases4))
        for username,lease:=range c.manualClientLeases4{
            if _,ok:=c.users[username];!ok{return c,fmt.Errorf("manual lease account not in protected roster")}
            p,e:=netip.ParsePrefix(lease)
            if e!=nil||!p.Addr().Is4()||p.Bits()!=32||p.String()!=lease||
                p.Addr().IsUnspecified()||p.Addr().IsMulticast()||
                p.Addr().IsLoopback()||p.Addr().IsLinkLocalUnicast()||
                seen[p.Addr()]{return c,fmt.Errorf("manual lease must be unique canonical IPv4 /32")}
            seen[p.Addr()]=true
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
    switch *startupPadding{
    case "off":c.startupPaddingMode=0
    case "tls":c.startupPaddingMode=1
    case "flows":c.startupPaddingMode=2
    default:return c,fmt.Errorf("startup-padding must be off, tls or flows")
    }
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
    }else if *usersFile!=""||*leasePool!=""||*manualLease!=""||*manualLeasesFile!=""{
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
    // The raw AF_PACKET socket is always scoped to --raw-interface and
    // validates destination IPv4. Server 0.0.0.0 is a CONFIGURATION ALIAS,
    // not an unfiltered receive wildcard or a TCP listen(2) binding.
    // The real interface IPv4 is resolved before any TUN/routing side effects.
    if role=="server"&&*ip=="" {*ip="0.0.0.0"}
    parsed,err:=netip.ParseAddr(*ip)
    if err!=nil||!parsed.Is4(){return c,fmt.Errorf("local-ip requires IPv4, or server 0.0.0.0/omitted for --raw-interface auto-selection")}
    if role=="client"&&parsed.IsUnspecified(){
        return c,fmt.Errorf("client local-ip must be a concrete IPv4")
    }
    c.localIP=parsed
    c.rawInterface=*iface
    c.localPort=uint16(*port)
    c.tunName=*tunName
    c.tunCIDR=*tunCIDR
    c.serverName=*name
    if *decoy!="" {
        if role!="server"{return c,fmt.Errorf("decoy is server-only")}
        host,portText,e:=net.SplitHostPort(*decoy)
        if e!=nil||host==""||strings.TrimSpace(host)!=host{return c,fmt.Errorf("decoy needs fixed host:port")}
        targetPort,e:=strconv.Atoi(portText)
        if e!=nil||targetPort<1||targetPort>65535{return c,fmt.Errorf("decoy port invalid")}
        if host==c.localIP.String()&&uint16(targetPort)==c.localPort{return c,fmt.Errorf("decoy cannot target own raw listener")}
        if c.gameLanes>0{return c,fmt.Errorf("decoy requires shared/normal server entry; legacy fixed Game listener has no ordinary TLS dispatch")}
        c.decoyTarget=*decoy
    }
    c.username=*user
    c.password=*pass
    if *routeShort!="" {
        if *route!=""||*routeFile!="" {return c,fmt.Errorf("route-key, route-key-hex and route-key-hex-file are mutually exclusive")}
        cachePath:=*routeCache
        if cachePath=="" {cachePath,err=v4routekey.DefaultCachePath(role,*name);if err!=nil{return c,err}}
        c.routeKey,_,err=v4routekey.Resolve(*routeShort,cachePath)
        if err!=nil{return c,fmt.Errorf("invalid/persisted route-key: %w",err)}
    }else{
        if *routeCache!="" {return c,fmt.Errorf("route-key-cache-file requires short route-key")}
        c.routeKey,err=hex.DecodeString(*route)
        if err!=nil||len(c.routeKey)!=32{
            return c,fmt.Errorf("route-key (8..32 alphanumeric) or legacy 32-byte route-key-hex required; no online bootstrap")
        }
    }
    if role=="server"&&*verifyTLS{return c,fmt.Errorf("tls-verify-server is client-only")}
    c.tlsVerifyServer=role=="client"&&*verifyTLS
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
    if runtime.GOOS=="android"&&role=="client"{
        if !c.tlsVerifyServer{
            log.Print("V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_MODE role=client class=DISABLED")
        }else{
            log.Print("V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_MODE role=client class=ENABLED")
            if c.tlsRoots==nil{log.Print("V4_PUBLIC_ANDROID_TLS_TRUST_SOURCE role=client class=OS_STORE")
            }else{log.Print("V4_PUBLIC_ANDROID_TLS_TRUST_SOURCE role=client class=APP_PEM")}
        }
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
    if role=="client"&&!c.autoIP&&*tunnel==""{
        install,e:=logicaltunnel.ResolveInstallation("",*installPath,false)
        if e!=nil{return c,fmt.Errorf("installation-id-file: %w",e)}
        c.installation=install
        c.tunnel=logicaltunnel.DerivedTunnelID(c.username,install)
    }
    if c.tunnel==[16]byte{}&&!(role=="server"&&(c.leasePool.IsValid()||len(c.manualClientLeases4)>0||c.mixedModes)){
        return c,fmt.Errorf("manual tunnel-id required without auto-IP/lease-pool")
    }
    if role=="server"{
        if *cert==""||*key==""{return c,fmt.Errorf("tls-cert and tls-key required")}
        c.tlsCert=*cert;c.tlsKey=*key
    }else{
        if *peerHost!=""{
            if runtime.GOOS!="android"||!dnsnative.ValidBootstrapHostname(*peerHost){
                return c,fmt.Errorf("peer-host requires a valid Android physical bootstrap DNS name")
            }
            c.peerHost=*peerHost
        }else{
            parsed,err=netip.ParseAddr(*peer)
            if err!=nil||!parsed.Is4(){return c,fmt.Errorf("peer-ip requires IPv4")}
            c.peerIP=parsed
        }
        if *remotePort==0||*remotePort>65535{return c,fmt.Errorf("peer-port invalid")}
        c.peerPort=uint16(*remotePort)
    }
    tunPrefix,e:=netip.ParsePrefix(*tunCIDR)
    if e!=nil||!tunPrefix.Addr().Is4(){return c,fmt.Errorf("invalid tun-ipv4")}
    if c.serverIPv6Carrier&&(!tunPrefix.Addr().IsPrivate()||tunPrefix.Bits()<16||tunPrefix.Bits()>30){
        return c,fmt.Errorf("IPv6 carrier requires server private IPv4 TUN /16..30, same /16 as authenticated clients")
    }
    if role=="server"&&c.mixedModes&&!c.leasePool.IsValid(){
        c.leasePool,e=defaultV4ServerLeasePool(tunPrefix,c.manualClientLeases4)
        if e!=nil{return c,e}
    }
    if role=="server"&&c.manualClientLease4.IsValid(){
        if !tunPrefix.Contains(c.manualClientLease4.Addr())||
           c.manualClientLease4.Addr()==tunPrefix.Addr(){
            return c,fmt.Errorf("manual client /32 must be distinct from server TUN IPv4 inside its owned subnet")
        }
    }
    if role=="server"&&len(c.manualClientLeases4)>0{
        for _,lease:=range c.manualClientLeases4{
            p,e:=netip.ParsePrefix(lease)
            if e!=nil||!tunPrefix.Contains(p.Addr())||p.Addr()==tunPrefix.Addr(){
                return c,fmt.Errorf("manual per-account /32 must be inside owned TUN subnet, excluding server")
            }
            if c.leasePool.IsValid()&&c.leasePool.Contains(p.Addr()){
                return c,fmt.Errorf("manual account /32 collides with automatic pool")
            }
        }
    }
    if c.serverIPv6Carrier&&!c.leasePool.IsValid()&&!c.manualClientLease4.IsValid()&&len(c.manualClientLeases4)==0{
        return c,fmt.Errorf("IPv6 carrier requires server-owned authenticated IPv4 lease pool or manual lease")
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
    if err!=nil&&runtime.GOOS=="android"&&errors.Is(err,os.ErrNotExist){
        // Android kernels expose the SAME real char TUN under either path;
        // only ENOENT warrants a second path. The exact TUNSETIFF ioctl
        // still authenticates a true IFF_TUN|IFF_NO_PI descriptor.
        fd,err=os.OpenFile("/dev/tun",os.O_RDWR,0)
    }
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

type ownedServerMasquerade struct{
    rule []string
    command func(...string)([]byte,error)
    active bool
}
// Each server process installs exactly one uniquely tagged POSTROUTING rule
// scoped to its own TUN IPv4 subnet and the explicitly selected underlay.
// Never flush chains, edit other services' rules or touch host sysctls.
func linuxMasqueradeRule(c config,tag string)([]string,error){
    if c.role!="server"||tag==""||strings.IndexFunc(tag,func(r rune)bool{
        return !(r>='a'&&r<='z'||r>='0'&&r<='9'||r=='-')
    })>=0{return nil,fmt.Errorf("invalid server NAT owner tag")}
    prefix,e:=netip.ParsePrefix(c.tunCIDR)
    if e!=nil||!prefix.Addr().Is4()||prefix.Bits()>30||
       c.rawInterface==""||c.rawInterface==c.tunName{
        return nil,fmt.Errorf("invalid server TUN/underlay MASQUERADE scope")
    }
    return []string{"-s",prefix.Masked().String(),"-o",c.rawInterface,
        "-m","comment","--comment",tag,"-j","MASQUERADE"},nil
}
func linuxMasqueradeCommand(args ...string)([]byte,error){
    return exec.Command("iptables",append([]string{"-w","3"},args...)...).CombinedOutput()
}
func installOwnedServerMasquerade(c config,
    command func(...string)([]byte,error))(*ownedServerMasquerade,error){
    if c.role!="server"||command==nil{return nil,fmt.Errorf("server NAT requires owned command")}
    var token [8]byte
    if _,e:=rand.Read(token[:]);e!=nil{return nil,fmt.Errorf("server NAT owner ID: %w",e)}
    rule,e:=linuxMasqueradeRule(c,"wbd-v4-"+hex.EncodeToString(token[:]))
    if e!=nil{return nil,e}
    obj:=&ownedServerMasquerade{rule:rule,command:command}
    args:=append([]string{"-t","nat","-I","POSTROUTING","1"},rule...)
    if out,e:=command(args...);e!=nil{return nil,fmt.Errorf("add owned IPv4 MASQUERADE: %w: %s",e,out)}
    obj.active=true
    check:=append([]string{"-t","nat","-C","POSTROUTING"},rule...)
    if out,e:=command(check...);e!=nil{
        return nil,errors.Join(fmt.Errorf("MASQUERADE kernel readback: %w: %s",e,out),obj.Close())
    }
    // IPv4 forwarding is a global security policy, not owned by this TUN.
    // Tell the operator if it is disabled; never silently claim internet egress.
    if b,e:=os.ReadFile("/proc/sys/net/ipv4/ip_forward");e==nil&&strings.TrimSpace(string(b))!="1"{
        log.Printf("V4_PUBLIC_SERVER_NAT_WARNING ip_forward=0 owner_rule_applied=1 external_forwarding_not_ready=1")
    }
    log.Printf("V4_PUBLIC_SERVER_MASQUERADE_APPLIED tun_subnet=%s underlay=%s tag=%s kernel_readback=1",
        rule[1],c.rawInterface,rule[7])
    return obj,nil
}
func(n *ownedServerMasquerade)Close()error{
    if n==nil||!n.active{return nil}
    args:=append([]string{"-t","nat","-D","POSTROUTING"},n.rule...)
    out,e:=n.command(args...)
    if e!=nil{return fmt.Errorf("owned MASQUERADE delete failed, rule preserved: %w: %s",e,out)}
    n.active=false
    log.Printf("V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED owned_rule_deleted=1")
    return nil
}

func originalRandomISN()(uint32,error){
    var b [4]byte
    if _,err:=rand.Read(b[:]);err!=nil{return 0,err}
    n:=binary.BigEndian.Uint32(b[:])
    if n==0{return 1,nil}
    return n,nil
}
var errPublicNativePeerDead=errors.New("original Rust authenticated peer dead; Go cold TLS reauthorization required")
var errPublicNativePhysicalScopeLost=errors.New("Android original Rust underlay Network/ifindex invalid; withdraw UID route and stop, no cold retry")

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
 live func()bool,pulse func()(realityfront.V4PublicLoopPulse,error),
 predead ...chan<- struct{})error{
 ticker:=time.NewTicker(time.Second);defer ticker.Stop()
 predeadNotified:=false
 for{select{
 case <-ctx.Done():return nil
 case e:=<-errs:return e
 case <-ticker.C:
  if !live(){continue}
  stats,e:=pulse()
  if e!=nil{continue}
  if stats.PhysicalScopeInvalid{
   // This is not authenticated peer-dead evidence and must not permit
   // cold TLS reauth. Stop the old route and owner immediately.
   return errPublicNativePhysicalScopeLost
  }
  if publicNativeHealthDead(stats){return errPublicNativePeerDead}
  // Only original *client* preterminal Health evidence can request
  // cold B. One notification per exact generation; it does not
  // alter Rust Health dead90, local TLS, TUN route or native Stop.
  if !predeadNotified&&stats.AuthenticatedPeerPreDead&&
      len(predead)>0&&predead[0]!=nil{
      select{case predead[0]<-struct{}{}:default:}
      predeadNotified=true
  }
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
// chooseUnderlayIPv4 chooses one exact AF_PACKET destination address of
// the operator-selected Linux interface. It never changes the negotiated
// peer endpoint or makes the socket receive arbitrary destination addresses.
// Multiple eligible addresses are ambiguous and must be selected explicitly.
func chooseUnderlayIPv4(addrs []net.Addr)(netip.Addr,error){
    var found netip.Addr
    for _,entry:=range addrs{
        prefix,err:=netip.ParsePrefix(entry.String())
        if err!=nil{continue}
        addr:=prefix.Addr()
        if !addr.Is4()||addr.IsUnspecified()||addr.IsMulticast()||
           addr.IsLoopback()||addr.IsLinkLocalUnicast(){continue}
        if found.IsValid()&&found!=addr{
            return netip.Addr{},fmt.Errorf("raw-interface has multiple IPv4 addresses; specify one via --local-ip")
        }
        found=addr
    }
    if !found.IsValid(){
        return netip.Addr{},fmt.Errorf("raw-interface has no usable non-loopback IPv4; specify --local-ip explicitly")
    }
    return found,nil
}

// Android-only privacy-preserving cold parse diagnosis. Never log
// err.Error(), raw argv, private paths, SNI, UID, route keys or passwords.
// Categories are stable; every original parse failure still fails closed.
func originalAndroidColdParseClass(err error)string{
 if err==nil{return "OTHER"}
 s:=err.Error()
 switch{
 case strings.HasPrefix(s,"flag provided but not defined:")||
      strings.HasPrefix(s,"invalid value ")||
      strings.HasPrefix(s,"flag needs an argument:"):
  return "FLAG_SYNTAX"
 case strings.HasPrefix(s,"invalid password-file:"):
  return "PASSWORD_FILE"
 case strings.HasPrefix(s,"invalid route-key-hex-file:")||
      strings.HasPrefix(s,"invalid route-key-file:"):
  return "ROUTE_KEY_FILE"
 case strings.Contains(s,"route-key")||
      strings.HasPrefix(s,"invalid/persisted route-key"):
  return "ROUTE_KEY_VALUE"
 case strings.HasPrefix(s,"installation-id-file:"):
  return "INSTALLATION_ID"
 case strings.HasPrefix(s,"signed Android CN8503 cold source rejected:"):
  return "CN_GEOSITE_FILE"
 case strings.HasPrefix(s,"load server TLS trust PEM:")||
      strings.HasPrefix(s,"invalid TLS trust PEM")||
      strings.HasPrefix(s,"trusted server TLS PEM"):
  return "TLS_CA_FILE"
 case strings.Contains(s,"excluded app ID")||
      strings.Contains(s,"Android UID group")||
      strings.Contains(s,"Android route UID")||
      strings.Contains(s,"all-app routing")||
      strings.Contains(s,"all-app mode")||
      strings.Contains(s,"bounded exclusions")||
      strings.Contains(s,"Android all-app")||
      strings.Contains(s,"Android single and group UID")||
      strings.Contains(s,"Android exclude IDs"):
  return "ALL_APP_EXCLUSIONS"
 case strings.Contains(s,"Android root client needs explicit physical Network handle")||
      strings.Contains(s,"Android Network/routing parameters"):
  return "ANDROID_NETWORK_SCOPE"
 case strings.HasPrefix(s,"peer-ip")||
      strings.HasPrefix(s,"peer-host")||
      strings.HasPrefix(s,"Android peer-host and peer-ip"):
  return "PEER_ADDRESS"
 case strings.HasPrefix(s,"missing/invalid real original V4 TLS/raw/TUN settings"):
  return "REQUIRED_COLD_SETTINGS"
 case strings.Contains(s,"outer-mtu")||
      strings.Contains(s,"tun-txqlen")||
      strings.Contains(s,"tun-fq-")||
      strings.Contains(s,"outer-repair")||
      strings.Contains(s,"auto-ip")||
      strings.Contains(s,"rotation")||
      strings.Contains(s,"mode")||
      strings.Contains(s,"startup-padding"):
  return "POLICY"
 default:return "OTHER"
 }
}

// A36: invoked by the APK Restore button as the SAME signed original-Go
// Bionic native ELF, without credentials, server details or any FakeTCP SYN.
// Call only after the exact previous Go/Rust owner has stopped/joined.
// This deliberately does NOT flush system firewall, routes, DNS or VPN.
func recoverOriginalAndroidRootOwned()error{
    if runtime.GOOS!="android"||os.Geteuid()!=0{
        return fmt.Errorf("exact Android root Restore requires euid 0")
    }
    runIP:=func(args ...string)(string,error){
        c,cancel:=context.WithTimeout(context.Background(),3*time.Second)
        defer cancel()
        b,e:=exec.CommandContext(c,"ip",args...).CombinedOutput()
        if len(b)>1024<<10{return "",fmt.Errorf("owned ip readback oversized")}
        if e!=nil{return "",fmt.Errorf("owned ip mutation/readback failed")}
        return string(b),nil
    }
    firewall,err:=exec.LookPath("iptables")
    if err!=nil{
        log.Print("V4_PUBLIC_ANDROID_RESTORE_RST_FAILED role=client")
        return fmt.Errorf("original Root Restore missing scoped firewall")
    }
    runFirewall:=func(args ...string)(string,error){
        c,cancel:=context.WithTimeout(context.Background(),3*time.Second)
        defer cancel()
        b,e:=exec.CommandContext(c,firewall,args...).CombinedOutput()
        if len(b)>256<<10{return "",fmt.Errorf("scoped firewall readback oversized")}
        if e!=nil{return "",fmt.Errorf("scoped firewall command failed")}
        return string(b),nil
    }
    const root="/data/local/tmp/wbd-next-root/"
    tetherErr:=rootjournal.RecoverTether(runIP,runFirewall,root+"tether-journal.json")
    runFirewall6:=func(args ...string)(string,error){
        c,cancel:=context.WithTimeout(context.Background(),3*time.Second)
        defer cancel()
        b,e:=exec.CommandContext(c,"ip6tables",args...).CombinedOutput()
        if len(b)>256<<10||e!=nil{return "",fmt.Errorf("scoped IPv6 firewall command failed")}
        return string(b),nil
    }
    ipv6Err:=rootjournal.RecoverIPv6CarrierBatch(runIP,runFirewall,runFirewall6,originalIPv6Batch,root+"ipv6-carrier-journal.json")
    systemDNS6Err:=rootjournal.RecoverSystemDNS6(runIP,runFirewall6,nil,nil,root+"system-dns6-journal.json")
    systemDNSErr:=rootjournal.RecoverSystemDNS(runIP,runFirewall,nil,nil,root+"system-dns-journal.json")
    dnsErr:=rootjournal.RecoverDNS(runIP,runFirewall,nil,root+"dns-tcp-journal.json")
    _,routeErr:=rootjournal.RecoverOwned(runIP,root+"route-journal.json",originalIPv6Batch)
    routeErr=errors.Join(ipv6Err,systemDNS6Err,systemDNSErr,dnsErr,tetherErr,routeErr)
    if routeErr!=nil{log.Print("V4_PUBLIC_ANDROID_RESTORE_ROUTE_FAILED role=client")}else{
        log.Print("V4_PUBLIC_ANDROID_RESTORE_ROUTE_CLEARED role=client")
    }
    _,rstErr:=rstguard.RecoverOwned(runFirewall,root+"rst-guard.json")
    if rstErr!=nil{log.Print("V4_PUBLIC_ANDROID_RESTORE_RST_FAILED role=client")}else{
        log.Print("V4_PUBLIC_ANDROID_RESTORE_RST_CLEARED role=client")
    }
    if routeErr!=nil||rstErr!=nil{
        return fmt.Errorf("original Root Restore not fully verified; owned journal retained on uncertain state")
    }
    log.Print("V4_PUBLIC_ANDROID_RESTORE_NATIVE_KERNEL_CLEARED role=client")
    return nil
}

func Run(role string,args []string)(retErr error){
 if runtime.GOOS=="android"&&role=="client"{
  // Actual original Go Bionic ELF entry, NOT an emulated TLS/Root stage.
  log.Print("V4_PUBLIC_ANDROID_GO_ENTRY role=client")
 }
 if runtime.GOOS=="android"&&role=="client"&&len(args)==1&&args[0]=="--android-recover-owned-root"{
     return recoverOriginalAndroidRootOwned()
 }
 if role=="server"&&len(args)==2&&args[0]=="--init-route-key-file"{
   return initServerRouteKeyFile(args[1])
 }
 cfg,err:=parse(role,args)
    if err!=nil{
        if runtime.GOOS=="android"&&role=="client"{
            // Emit only a source-locked category, not the original error
            // which may contain sensitive user-supplied file paths.
            log.Printf("V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=%s",
                originalAndroidColdParseClass(err))
        }
        return err
    }
    if runtime.GOOS=="android"&&role=="client"{
        log.Print("V4_PUBLIC_ANDROID_GO_ARGS_ACCEPTED role=client")
    }
    if runtime.GOOS=="android"&&cfg.androidCNSnapshot!=nil{
        // Verified file/typed rules only; NOT real Android system DNS.
        stats:=cfg.androidCNSnapshot.Stats()
        log.Printf("V4_PUBLIC_ANDROID_CN8503_COLD_FILE_VERIFIED count=%d sha256=%s dns_capture=NOT_CONNECTED",stats.Total,stats.SHA256)
    }
    iface,err:=net.InterfaceByName(cfg.rawInterface)
    if err!=nil{return err}
    if runtime.GOOS=="android"&&role=="client"{
        log.Print("V4_PUBLIC_ANDROID_GO_INTERFACE_FOUND role=client")
    }
    if runtime.GOOS=="android"{
        if role!="client"||cfg.androidNetworkHandle==0||iface.MTU<68||iface.MTU>65535{
            return fmt.Errorf("Android physical Network/MTU unavailable")
        }
        if (cfg.gameLanes!=0&&cfg.gameLanes!=2&&cfg.gameLanes!=4)||cfg.mixedModes||
           !cfg.disableOuterRepair||
           !cfg.autoIP||cfg.rotationInterval!=0{
            return fmt.Errorf("Android Root original Normal/Fixed/Auto and Game2/4 fixed/off only; rotation/outer-repair unavailable")
        }
        cfg.androidPhysicalMTU=uint32(iface.MTU)
        if cfg.androidClatParent!=""||cfg.androidClatPrefix!=""{
            if err=checkOriginalAndroidCLAT(cfg);err!=nil{return err}
        }
        cfg.androidPhysicalDNSDial,err=dnsnative.NewAndroidPhysicalDNSDialerWithUpstream(
            dnsnative.PhysicalScope{
                NetworkHandle:cfg.androidNetworkHandle,
                InterfaceName:cfg.rawInterface,
                IfIndex:iface.Index,
                MTU:iface.MTU,
                LocalIPv4:cfg.localIP,
            },cfg.androidPhysicalDNSUpstream)
        if err!=nil{
            return fmt.Errorf("Android physical DNS cold Network scope denied: %w",err)
        }
        // This is scope construction, not an outbound DNS socket or proof
        // of System Resolver interception/physical netd permission.
        log.Print("V4_PUBLIC_ANDROID_PHYSICAL_DNS_COLD_SCOPE_CHECKED socket_opened=0 dns_capture=NOT_CONNECTED")
        if cfg.peerHost!=""{
            // Original Go cold DNS wire/ID/QNAME and scoped Bionic netd
            // UDP/TCP socket. Use the single configured physical upstream;
            // DNS failure aborts before the first original FakeTCP SYN.
            dnsCtx,cancelDNS:=context.WithTimeout(context.Background(),5*time.Second)
            resolved,resolveErr:=dnsnative.ResolveBootstrapIPv4WithUpstream(
                dnsCtx,cfg.peerHost,cfg.androidPhysicalDNSDial,cfg.androidPhysicalDNSUpstream)
            cancelDNS()
            if resolveErr!=nil{
                return fmt.Errorf("Android physical server bootstrap failed before FakeTCP SYN: %w",resolveErr)
            }
            cfg.peerIP=resolved
            log.Printf("V4_PUBLIC_ANDROID_SERVER_BOOTSTRAP_PHYSICAL_RESOLVED host=%s dns=%s udp_tcp53_original_go=1",cfg.peerHost,cfg.androidPhysicalDNSUpstream)
        }
        if cfg.androidClatParent!=""{
            // Read the actual selected Network route before any FakeTCP
            // SYN. The original RAW bind and M4 still own all traffic.
            mark:=fmt.Sprintf("0x%x",uint32(cfg.androidNetworkHandle>>32)|0xf0000)
            routeCtx,cancel:=context.WithTimeout(context.Background(),3*time.Second)
            output,e:=exec.CommandContext(routeCtx,"ip","-4","route","get",cfg.peerIP.String(),
                "from",cfg.localIP.String(),"oif",cfg.rawInterface,"mark",mark,"uid","0").CombinedOutput()
            cancel()
            if e!=nil||!rootjournal.SelectedUIDRouteGetUsesTun(string(output),cfg.rawInterface){
                return fmt.Errorf("Android CLAT route is not the selected Network IPv4 translation path")
            }
            log.Printf("V4_PUBLIC_ANDROID_CLAT_ROUTE_READBACK role=client interface=%s parent=%s ipv4_mtu=%d",
                cfg.rawInterface,cfg.androidClatParent,iface.MTU)
        }
    }
    if role=="server"&&cfg.localIP.IsUnspecified(){
        addresses,e:=iface.Addrs()
        if e!=nil{return fmt.Errorf("inspect server raw-interface IPv4: %w",e)}
        cfg.localIP,e=chooseUnderlayIPv4(addresses)
        if e!=nil{return e}
        log.Printf("V4_PUBLIC_SERVER_UNDERLAY_BIND interface=%s local_ip=%s mode=auto_interface_ipv4 port=%d nat_port_forward_required_if_behind_gateway",
                   cfg.rawInterface,cfg.localIP,cfg.localPort)
    }
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
    if runtime.GOOS=="android"&&role=="client"{
        log.Print("V4_PUBLIC_ANDROID_GO_TUN_OPEN_ATTEMPTED role=client")
    }
    tun,err:=openTun(cfg.tunName,cfg.tunCIDR,cfg.innerMTU)
    if err!=nil{return err}
    if runtime.GOOS=="android"&&role=="client"{
        log.Print("V4_PUBLIC_ANDROID_GO_TUN_OPENED role=client")
    }
    // The Go cold lifetime owns TUN; each Rust generation Stop joins and
    // releases kernel loans before the FINAL Go close or a fresh TLS generation.
    connected:=false
    defer func(){retErr=errors.Join(retErr,tun.Close())}()
    // Server-only owned NAT rule; cleanup is deferred AFTER TUN so it
    // runs first, with the original Rust Stop/driver loan lifecycle intact.
    if role=="server"{
        nat,e:=installOwnedServerMasquerade(cfg,linuxMasqueradeCommand)
        if e!=nil{return e}
        defer func(){retErr=errors.Join(retErr,nat.Close())}()
    }
    if cfg.serverIPv6Carrier{
        owner,e:=startOriginalServerIPv6Carrier(cfg,tun)
        if e!=nil{return e}
        defer func(){retErr=errors.Join(retErr,owner.Stop())}()
    }
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
    if role=="client"&&cfg.autoIP&&runtime.GOOS!="android"{
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
    if runtime.GOOS=="android"&&role=="client"&&(cfg.gameLanes==2||cfg.gameLanes==4){
        // B41 genuine original-Go dual TLS/FakeTCP on selected Network,
        // one original Rust GameAdapter and M4, exact Root UID route after
        // both lane Detach/readback. No Go DATA worker and no Game4.
        ctx,stop:=signal.NotifyContext(context.Background(),os.Interrupt,syscall.SIGTERM)
        defer stop()
        return runAndroidGame(ctx,cfg,uint32(iface.Index),tun,&connected)
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
    if role=="client"&&cfg.autoIP&&runtime.GOOS!="android"{
        // PLAN028 only for real protected automatic IPv4 on Linux Normal.
        // The one process-shared Rust TUN reader already exists above and
        // remains owned across simultaneous A+B TLS/native generations.
        return runOriginalLinuxClientPaths(ctx,cfg,tun)
    }
    // A35: The real Linux netns oracle drops kernel-generated TCP RST on
        // BOTH FakeTCP endpoints. Android root must own a narrower single-flow
        // equivalent before initial SYN; otherwise SYNACK can trigger a native
        // kernel RST that kills a valid server session before ClientHello.
        // All operations are cold/root-only, with an exact durable owner journal.
        if runtime.GOOS=="android"&&role=="client"{
            if os.Geteuid()!=0{
                log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=IPTABLES_UNAVAILABLE")
                return fmt.Errorf("Android root FakeTCP RST guard requires effective uid 0")
            }
            iptables,findErr:=exec.LookPath("iptables")
            if findErr!=nil{
                log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=IPTABLES_UNAVAILABLE")
                return fmt.Errorf("Android rooted iptables binary not available")
            }
            runFirewall:=func(args ...string)(string,error){
                limited,cancel:=context.WithTimeout(context.Background(),3*time.Second)
                defer cancel()
                cmd:=exec.CommandContext(limited,iptables,args...)
                out,e:=cmd.CombinedOutput()
                if len(out)>256<<10{return "",fmt.Errorf("bounded iptables diagnostic output exceeded")}
                if e!=nil{return "",fmt.Errorf("scoped iptables call failed")}
                return string(out),nil
            }
            const journal="/data/local/tmp/wbd-next-root/rst-guard.json"
            guard,recovered,guardErr:=rstguard.New(runFirewall,journal,rstguard.Plan{
                Version:1,Interface:cfg.rawInterface,SourceIP:cfg.localIP.String(),
                PeerIP:cfg.peerIP.String(),SourcePort:int(cfg.localPort),
                PeerPort:int(cfg.peerPort),
            })
            if guardErr!=nil{
                log.Printf("V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=%s",rstguard.Class(guardErr))
                return fmt.Errorf("Android original FakeTCP exact RST guard refused")
            }
            if recovered{log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_RECOVERED role=client")}
            log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_READY role=client")
            defer func(){
                if dropped,known:=guard.DropCounter();known{
                    if dropped>0{
                        log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_MATCHED_RST_DROP role=client")
                    }else{
                        log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_NO_RST_DROP role=client")
                    }
                }else{
                    log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_COUNTER_UNAVAILABLE role=client")
                }
                if closeErr:=guard.Close();closeErr!=nil{
                    log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_STOP_UNVERIFIED role=client")
                    retErr=errors.Join(retErr,fmt.Errorf("Android exact RST guard Stop did not verify"))
                }else{
                    log.Print("V4_PUBLIC_ANDROID_COLD_RST_GUARD_STOP_CLEARED role=client")
                }
            }()
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
        // Before any genuine FakeTCP SYN or standard ClientHello: select only
        // the cold raw sender's exact Android physical Network. The AF_PACKET
        // receiver is already bound to this interface by original Go.
        if err=raw.BindAndroidNetwork(cfg.androidNetworkHandle,
            cfg.rawInterface,iface.Index,iface.MTU);err!=nil{
            _=raw.Close()
            return err
        }
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
func logNormalStartupPadding(role string,fec bool,mode string,records,bytes uint64,err error){
    label:="V4_PUBLIC_NORMAL_PADDING"
    if fec{label="V4_PUBLIC_FEC_SOURCE_PADDING"}
    if err!=nil{
        log.Printf("%s_UNAVAILABLE role=%s error=%v",label,role,err)
        return
    }
    log.Printf("%s_RAW_RECEIPT role=%s mode=%s padded_records=%d padded_bytes=%d original_TLS_Rust_M4=1 real_AF_PACKET_send=1",
        label,role,mode,records,bytes)
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
// A41: Android's real kernel interface/address enumeration is already used
// for the physical Network in the original Root client. Reuse that *same*
// native getifaddrs path for the newly-owned TUN after protected /32 has
// been applied. Android's external "ip -j addr" can reject JSON output or
// have a different shape even when "ip -j link" worked earlier.
// Linux's existing JSON path stays unchanged.
func originalV4OwnedTunIPv4FromNativeAddrs(addrs []net.Addr)(netip.Prefix,error){
    var owned netip.Prefix
    for _,a:=range addrs{
        ipNet,ok:=a.(*net.IPNet)
        if !ok{return netip.Prefix{},fmt.Errorf("non-IP native TUN address")}
        raw4:=ipNet.IP.To4()
        if raw4==nil{continue} // IPv6 never becomes an IPv4 lease
        ones,bits:=ipNet.Mask.Size()
        if bits!=32||ones!=32||owned.IsValid(){
            return netip.Prefix{},fmt.Errorf("native TUN has non-/32 or multiple IPv4 addresses")
        }
        ip,ok:=netip.AddrFromSlice(raw4)
        if !ok||!ip.Is4()||ip.IsUnspecified()||ip.IsMulticast(){
            return netip.Prefix{},fmt.Errorf("native TUN has invalid IPv4")
        }
        owned=netip.PrefixFrom(ip,32)
    }
    if !owned.IsValid(){return netip.Prefix{},fmt.Errorf("native TUN has no IPv4")}
    return owned,nil
}
func readOwnedTunIPv4(name string)(netip.Prefix,error){
    if runtime.GOOS=="android"{
        iface,err:=net.InterfaceByName(name)
        if err!=nil{return netip.Prefix{},fmt.Errorf("native Android owned TUN lookup: %w",err)}
        if iface==nil||iface.Index<=0||iface.Name!=name{
            return netip.Prefix{},fmt.Errorf("native Android owned TUN identity mismatch")
        }
        addrs,err:=iface.Addrs()
        if err!=nil{return netip.Prefix{},fmt.Errorf("native Android TUN getifaddrs: %w",err)}
        return originalV4OwnedTunIPv4FromNativeAddrs(addrs)
    }
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
// Only the original OS address mutation/readback may emit these outcomes.
func originalAndroidPostauthGo(stage string){
    if runtime.GOOS=="android"{
        log.Printf("V4_PUBLIC_ANDROID_POSTAUTH role=client class=%s",stage)
    }
}
// A47: printable snapshots originate in the ONE real Rust RX FD and
// native worker; these are cumulative numeric observations, NOT app PASS.
func originalAndroidM4RxSnapshot(p realityfront.V4PublicLoopPulse)string{
 d:=p.RawDebug
 return fmt.Sprintf("V4_PUBLIC_ANDROID_M4_DIAG role=client kind=rx read=%d data=%d ack=%d tuple=%d ipck=%d tcpck=%d flags=%d len=%d opts=%d ttl0=%d other=%d seq=%d offer=%d recv_err=%d lastlen=%d lastttl=%d lastflags=%d src=%d dst=%d sport=%d dport=%d errno=%d",
 d[0],d[1],d[2],d[3],d[4],d[5],d[6],d[7],d[8],d[9],d[10],d[11],d[12],d[13],d[14],d[15],d[16],d[17],d[18],d[19],d[20],d[21])
}
func originalAndroidM4OwnerSnapshot(p realityfront.V4PublicLoopPulse)string{
 health:=0
 if p.AuthenticatedPeerControl{health=1}
 return fmt.Sprintf("V4_PUBLIC_ANDROID_M4_DIAG role=client kind=m4 poll=%d parse_fail=%d parsed=%d auth=%d rejected=%d writefail=%d tun=%d trej=%d rawtx=%d rtun=%d tcp=%d udp=%d icmp=%d dnsudp=%d dnstcp=%d dnsraw=%d dnsrtun=%d dnsptx=%d dnsprx=%d dnsperr=%d rxerr=%d txerr=%d health=%d",
 p.RawPollReady,p.RawParseFailed,p.RawParsed,p.RawAuthenticated,
 p.RawAuthRejected,p.ReverseTunWriteFailed,p.TunIPv4Admitted,
 p.TunIPv4Rejected,p.BusinessRawCopied,p.BusinessReverseTun,
 p.TunTCPSeen,p.TunUDPSeen,p.TunICMPSeen,p.DnsUDP53Seen,
 p.DnsTCP53Seen,p.DnsTunnelRawCopied,p.DnsTunnelReplyTun,
 p.DnsPhysicalTx,p.DnsPhysicalRx,p.DnsPhysicalError,
 p.RxErrors,p.TxErrors,health)
}
// A separate B6 numeric wire avoids changing historic A47/B3d/B4 M4
// snapshot formats; values come only from real Rust RAW/UDP/TUN operations.
func originalAndroidDNSB6Snapshot(p realityfront.V4PublicLoopPulse)string{
 return fmt.Sprintf("V4_PUBLIC_ANDROID_DNS_B6_DIAG role=client cnptx=%d noncnraw=%d tcpraw=%d ptctun=%d",
  p.DnsCNPhysicalSent,p.DnsNonCNTunnelRaw,p.DnsTCP53OriginalRaw,p.DnsPhysicalTCTun)
}
// Real original Rust M4 state, not Ready and never a guessed Chrome PASS.
func originalAndroidBusinessReceiptClasses(p realityfront.V4PublicLoopPulse)[]string{
 var stages []string
 if p.TunIPv4Admitted>0{stages=append(stages,"TUN_IPV4_SEEN")}
 if p.TunIPv4Rejected>0{stages=append(stages,"TUN_IPV4_REJECTED")}
 if p.BusinessRawCopied>0{stages=append(stages,"APP_RAW_TX_COPIED")}
 if p.BusinessReverseTun>0{stages=append(stages,"APP_REVERSE_TUN_WRITTEN")}
 if p.DnsUDP53Seen>0{stages=append(stages,"DNS_UDP53_TUN_SEEN")}
 if p.DnsTCP53Seen>0{stages=append(stages,"DNS_TCP53_TUN_SEEN")}
 if p.DnsTunnelRawCopied>0{stages=append(stages,"DNS_TUNNEL_RAW_COPIED")}
 if p.DnsTunnelReplyTun>0{stages=append(stages,"DNS_TUNNEL_REVERSE_TUN_WRITTEN")}
 if p.DnsPhysicalTx>0{stages=append(stages,"DNS_PHYSICAL_UDP_COPIED")}
 if p.DnsPhysicalRx>0{stages=append(stages,"DNS_PHYSICAL_REVERSE_TUN_WRITTEN")}
 if p.DnsPhysicalError>0{stages=append(stages,"DNS_PHYSICAL_ERROR")}
 if p.DnsCNPhysicalSent>0{stages=append(stages,"DNS_CN_PHYSICAL_SENT")}
 if p.DnsNonCNTunnelRaw>0{stages=append(stages,"DNS_NONCN_TUNNEL_RAW_COPIED")}
 if p.DnsTCP53OriginalRaw>0{stages=append(stages,"DNS_TCP53_ORIGINAL_RAW_COPIED")}
 if p.DnsPhysicalTCTun>0{stages=append(stages,"DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN")}
 if p.RawPollReady>0{stages=append(stages,"RAW_SOCKET_READABLE")}
 if p.RawParseFailed>0{stages=append(stages,"RAW_PARSE_FAILED")}
 if p.RawParsed>0{stages=append(stages,"RAW_PARSED")}
 if p.RawAuthenticated>0{stages=append(stages,"RAW_AUTHENTICATED")}
 if p.RawAuthRejected>0{stages=append(stages,"RAW_AUTH_REJECTED")}
 if p.ReverseTunWriteFailed>0{stages=append(stages,"REVERSE_TUN_WRITE_FAILED")}
 if p.TunICMPSeen>0{stages=append(stages,"TUN_ICMP_SEEN")}
 if p.TunTCPSeen>0{stages=append(stages,"TUN_TCP_SEEN")}
 if p.TunUDPSeen>0{stages=append(stages,"TUN_UDP_SEEN")}
 return stages
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
            if err:=runIP("addr","add",desired,"dev",tun.name);err!=nil{
                originalAndroidPostauthGo("LEASE_ADD_FAILED")
                return err
            }
            if err:=runIP("addr","del",tun.cidr,"dev",tun.name);err!=nil{
                originalAndroidPostauthGo("LEASE_DEL_FAILED")
                return err
            }
        }
        actual,err:=readOwnedTunIPv4(tun.name)
        if err!=nil{
            originalAndroidPostauthGo("LEASE_READBACK_FAILED")
            return err
        }
        if actual!=prefix{
            originalAndroidPostauthGo("LEASE_MISMATCH")
            return fmt.Errorf("client authenticated IPv4 OS readback mismatch")
        }
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

// Server B may not steal A's downlink from local TLS/native START alone.
// Unlike the client proof barrier, ordinary B uplink records are NOT enough:
// only its authenticated native client Health kind0, sent after B's RAW RX
// socket and worker start, proves the new remote receiver is present.
func waitOriginalNativeServerClientM4Ready(
    ctx context.Context,pulse func()(realityfront.V4PublicLoopPulse,error),
    promote func()error,max time.Duration,
)error{
    if ctx==nil||pulse==nil||promote==nil||max<=0{
        return fmt.Errorf("invalid original server client-native M4 readiness barrier")
    }
    timer:=time.NewTimer(max)
    ticker:=time.NewTicker(25*time.Millisecond)
    defer timer.Stop()
    defer ticker.Stop()
    for{
        status,err:=pulse()
        if err!=nil{return fmt.Errorf("new client M4 readiness evidence: %w",err)}
        if status.AuthenticatedPeerDead{
            return fmt.Errorf("candidate client native terminal before cold readiness")
        }
        if status.AuthenticatedPeerControl{
            return promote()
        }
        select{
        case <-ctx.Done():return ctx.Err()
        case <-timer.C:
            return fmt.Errorf("client B native M4 receiver not proven before bounded overlap deadline")
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
    // Original emitter and matching original AF_PACKET reader only.
    // This never creates an extra TCP sender or inspects payload content.
    var handoffCommitted atomic.Bool
    var firstPayloadTX atomic.Bool
    var firstPeerPayloadRX atomic.Bool
    observedEmit:=func(seg faketcp.Segment)error{
        e:=emit(seg)
        if e==nil&&runtime.GOOS=="android"&&len(seg.Payload)>0&&
           !handoffCommitted.Load()&&firstPayloadTX.CompareAndSwap(false,true){
            log.Print("V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_PAYLOAD_TX_OK role=client")
        }
        return e
    }
    assoc,err:=faketcp.NewClientAssociation(flow,isn,time.Second,observedEmit)
    if err!=nil{return err}
    defer assoc.Close()
    errs:=make(chan error,1)
    var goPostHandoffDataCopies atomic.Uint64
    var androidColdUntrustedRSTRecorded atomic.Bool
    go func(){
        for {
            seg,_,readErr:=raw.ReadSegment()
            if readErr!=nil{
                select{case <-ctx.Done():return;default:}
                select{case errs<-readErr:default:}
                return
            }
            if !flow.MatchesInbound(seg){continue}
            if runtime.GOOS=="android"&&len(seg.Payload)>0&&
               !handoffCommitted.Load()&&firstPeerPayloadRX.CompareAndSwap(false,true){
                log.Print("V4_PUBLIC_ANDROID_COLD_RAW_PEER_PAYLOAD_RX role=client")
            }
            // Exact original AF_PACKET inbound RST before TLS. This proves
            // only UNAUTHENTICATED wire failure, not server identity, M4
            // or application data; payload/IP/UID are never logged.
            if runtime.GOOS=="android" && seg.Flags&faketcp.FlagRST!=0 &&
               androidColdUntrustedRSTRecorded.CompareAndSwap(false,true){
                log.Printf("V4_PUBLIC_ANDROID_COLD_UNAUTH_RST_RX role=client source=original_filtered_af_packet")
            }
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
    if err:=assoc.Start(coldSynStart);err!=nil{
        // ANDROID ONLY, OBSERVABILITY ONLY: classify the exact original
        // syscall/client-association SYN send failure without logging IPv4,
        // credentials, keys, network handle, syscall arguments or packet.
        // Never transform the error, retry policy or original SYN bytes.
        if runtime.GOOS=="android"{
            category:="other"
            switch {
            case errors.Is(err,syscall.EPERM),errors.Is(err,syscall.EACCES):
                category="permission_denied"
            case errors.Is(err,syscall.ENETUNREACH),errors.Is(err,syscall.EHOSTUNREACH),
                 errors.Is(err,syscall.ENETDOWN):
                category="network_unreachable"
            case errors.Is(err,syscall.EINVAL),errors.Is(err,syscall.EAFNOSUPPORT):
                category="invalid_argument"
            case errors.Is(err,syscall.EADDRNOTAVAIL):
                category="source_unavailable"
            case errors.Is(err,syscall.ENOBUFS):
                category="buffer_pressure"
            }
            log.Printf("V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=%s",category)
        }
        return err
    }
    // Start() calls the ORIGINAL fake TCP raw segment writer synchronously.
    // This means kernel Sendto returned success, NOT that a peer replied.
    if runtime.GOOS=="android"{
        log.Printf("V4_PUBLIC_ANDROID_COLD_SYN_TX_OK role=client source=original_go_raw")
    }
    dialCtx,cancel:=context.WithTimeout(ctx,20*time.Second)
    defer cancel()
    // A first SYN may precede server AF_PACKET bind just as a post-dead
    // SYN can. Drive the SAME original bounded FakeTCP RTO/MaxSYNRetries
    // at initial connect and cold reauth. Association freezes local MSS at
    // creation; retries cannot change SYN TCP options or skip TLS admission.
    err=waitForOriginalColdSYN(dialCtx,assoc)
    if err!=nil{return err}
    if runtime.GOOS=="android"{
        // Unlike a raw SYNACK candidate this proves the ORIGINAL client
        // Association accepted its sequence/flow and reached Established.
        log.Print("V4_PUBLIC_ANDROID_ORIGINAL_ASSOC_ESTABLISHED role=client")
    }
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
    var cn8503Raw []byte
    if c.androidCNDNSSplit{cn8503Raw=c.androidCNSnapshot.PinnedWire()}
    native,err:=realityfront.NewV4LinuxClientProduct(
        realityfront.V4LinuxClientProductConfig{
            NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            AndroidPhysicalNetworkHandle:c.androidNetworkHandle,
            AndroidPhysicalMTU:c.androidPhysicalMTU,
            AndroidTunnelDNS:c.androidTunnelDNS,
            AndroidTunnelDNSUpstream:c.androidTunnelDNSUpstream,
            AndroidPhysicalDNS:c.androidPhysicalDNS,
            AndroidPhysicalDNSUpstream:c.androidPhysicalDNSUpstream,
            AndroidCN8503Raw:cn8503Raw,
             HealthKeepaliveSeconds:c.androidNativeHealthSeconds,
            Tun:tun.f,TunName:c.tunName,SharedTun:c.sharedTun,
            CleanupOwnedNetwork:productNativeCleanup(c,tun),
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            ConfigureLeaseIPv4:applyLease,
            FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
            StartupPaddingMode:c.startupPaddingMode,OuterIPMTU:c.outerMTU,
        })
    if err!=nil{
        if runtime.GOOS=="android"{log.Print("V4_PUBLIC_ANDROID_COLD_PRODUCT_FAILED role=client")}
        return err
    }
    if runtime.GOOS=="android"{log.Print("V4_PUBLIC_ANDROID_COLD_PRODUCT_PREPARED role=client")}
    cfg:=realityfront.ClientAdmissionConfig{
        TLS:realityfront.ClientConfig{ServerName:c.serverName,RouteKey:c.routeKey,VerifyServer:c.tlsVerifyServer,RootCAs:c.tlsRoots,Timeout:15*time.Second},
        Username:c.username,Password:c.password,TunnelID:c.tunnel[:],
        AutoLease:c.autoIP,InstallationID:c.installation[:],
        ClientLimit:c.recordLimit,DesiredLanes:1,LaneID:1,Policy:policy,
    }
    nativeAdmissionStart:=time.Now()
    stopColdRTO:=driveOriginalClientColdBootstrapRTO(dialCtx,assoc)
    authenticated,err:=native.ConnectAuthenticatedPeer(dialCtx,assoc,cfg)
    resent,retryErr:=stopColdRTO()
    if resent>0{
        log.Printf("V4_PUBLIC_FAKETCP_CLIENT_COLD_DATA_RTO role=client mode=%s actual_original_retransmissions=%d post_detach=0",
            c.fecMode,resent)
    }
    if runtime.GOOS=="android"&&(err!=nil||retryErr!=nil){
        // NOT_OBSERVED refers to this one bounded Go-owned association.
        if !firstPayloadTX.Load(){log.Print("V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_PAYLOAD_TX_NOT_OBSERVED role=client")}
        if !firstPeerPayloadRX.Load(){log.Print("V4_PUBLIC_ANDROID_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED role=client")}
        if resent>0{log.Print("V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_RTO_OBSERVED role=client")}
    }
    if retryErr!=nil{originalAndroidPostauthGo("COLD_RTO_STOP_FAILED")}
    if err!=nil||retryErr!=nil{
        // Failed cold admission still owns a constructed native product.
        // It must release its loans/socket/generation before a new attempt.
        return errors.Join(err,retryErr,native.Close())
    }
    // Existing client product returns only after authenticated TLS detach,
    // exact Rust M4 RX attachment and native loop start.
    if assoc.State()!=faketcp.ClientAssociationDetached{
        originalAndroidPostauthGo("DETACH_STATE_FAILED")
        _=native.Close()
        return fmt.Errorf("Normal client Rust M4 started without FakeTCP detach")
    }
    // Android owns one original TLS session per Go RAW FD. After true
    // native M4 attach, completely quiesce ONLY that obsolete Go receiver.
    // Linux's original exact-tuple filtering remains unchanged.
    var rxHandoffErr error
    if runtime.GOOS=="android" {
        rxHandoffErr=raw.QuiesceDetachedClientReceive()
    }else{
        rxHandoffErr=raw.ExcludeDetachedData(flow.PeerIP,flow.PeerPort)
    }
    if rxHandoffErr!=nil{
        originalAndroidPostauthGo("GO_RX_FILTER_FAILED")
        _=native.Close()
        return fmt.Errorf("Normal client receive ownership handoff: %w",rxHandoffErr)
    }
    originalAndroidPostauthGo("GO_RX_FILTER_OK")
    handoffCommitted.Store(true)
    originalAndroidPostauthGo("GO_RX_HANDOFF_OK")
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
    // Only after genuine Go TLS credentials, a protected server-signed /32,
    // exact installed kernel address, Rust M4 workers AND DATA handoff may
    // Android grant ONE app UID a dedicated private route. Never a global
    // default/main-table route, VpnService, FakeIP or early pre-auth grant.
    var undoRootRoute func()error
    if runtime.GOOS=="android"&&(c.androidRouteAllApps||c.androidRouteUID!=0||len(c.androidRouteUIDs)>0){
        originalAndroidPostauthGo("UID_ROUTE_ENTERED")
        var authorizedLease string
        if authenticated==nil{
            return errors.Join(fmt.Errorf("missing real authenticated lease session"),native.Close())
        }
        authorizedLease,err=authenticated.AuthenticatedLeaseIPv4()
        if err==nil{
            undoRootRoute,err=androidRootRouteAfterNative(c,tun,authorizedLease)
        }
        if err!=nil{
            originalAndroidPostauthGo("UID_ROUTE_FAILED")
            return errors.Join(
            fmt.Errorf("Android exact original-Go authenticated routing denied: %w",err),
            native.Close(),
        )}
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
    var notifyPreDead chan<- struct{}
    if len(ready)>1{notifyPreDead=ready[1]}
    // Reuse the original one-second Health poll, no new worker or hot-path Go.
    businessLogged:=make(map[string]bool,6)
    var lastNumericM4 time.Time
    // B20: genuine original TLS+Rust FEC state, reported only on change
    // via the existing one-second native Health loop. No Go DATA callback,
    // extra timer, synthetic APPLIED or peer-reported boolean.
    var lastFecState realityfront.V4PublicFecReadback
    var fecStateObserved bool
    businessPulse:=func()(realityfront.V4PublicLoopPulse,error){
        p,e:=native.OriginalLoopPulse()
        if e==nil&&runtime.GOOS=="android"{
            if lastNumericM4.IsZero()||time.Since(lastNumericM4)>=4*time.Second{
                lastNumericM4=time.Now()
                log.Print(originalAndroidM4RxSnapshot(p))
                log.Print(originalAndroidM4OwnerSnapshot(p))
                log.Print(originalAndroidDNSB6Snapshot(p))
                if c.fecMode!=realityfront.FecV2Off{
                    state,readErr:=native.OriginalFECReadback()
                    if readErr==nil&&(!fecStateObserved||state!=lastFecState){
                        // Fixed enum + five native numeric fields only.
                        // Requested and PENDING are NOT business delivery.
                        log.Printf("V4_PUBLIC_ANDROID_FEC_STATE role=client mode=%s requested=%d applied=%d profile=%d pending=%t",
                            state.Mode,state.RequestedRevision,
                            state.AppliedRevision,state.Profile,state.Pending)
                        lastFecState=state
                        fecStateObserved=true
                    }
                }
            }
            for _,stage:=range originalAndroidBusinessReceiptClasses(p){
                if !businessLogged[stage]{
                    businessLogged[stage]=true
                    log.Printf("V4_PUBLIC_ANDROID_BUSINESS role=client class=%s",stage)
                }
            }
        }
        return p,e
    }
    err=monitorPublicNativePeer(ctx,errs,
        func()bool{return handoffCommitted.Load()},
        businessPulse,notifyPreDead)
    if runtime.GOOS=="android"{
        if final,e:=native.OriginalLoopPulse();e==nil{
            log.Print(originalAndroidM4RxSnapshot(final))
            log.Print(originalAndroidM4OwnerSnapshot(final))
            log.Print(originalAndroidDNSB6Snapshot(final))
        }
    }
    log.Printf("V4_PUBLIC_GO_RX_POST_HANDOFF role=client mode=%s go_data_full_copies=%d",c.fecMode,goPostHandoffDataCopies.Load())
    m,n,b,e:=native.OriginalNormalStartupPaddingCounters()
    logNormalStartupPadding("client",c.fecMode!=realityfront.FecV2Off,m,n,b,e)
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
    // Stop ordering: withdraw the only UID ingress route FIRST; only
    // thereafter stop/join original Rust RX/TX, release loans and TUN FD.
    // If cleanup cannot prove the kernel rule absent, return a hard error
    // and preserve the root-only journal for exact crash recovery.
    var routeErr error
    if undoRootRoute!=nil{
        routeErr=undoRootRoute()
        if routeErr==nil{
            log.Printf("V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client")
        }else{
            log.Printf("V4_PUBLIC_ANDROID_UID_ROUTE_STOP_UNPROVEN role=client err=%v",routeErr)
        }
    }
    closeErr:=errors.Join(routeErr,native.Close())
    if closeErr==nil{log.Printf("V4_PUBLIC_NATIVE_STOP_DRAINED role=client")}
    if err!=nil{return errors.Join(err,closeErr)}
    return closeErr
}
// Rust native owners have their own 32-lane cap; fake TCP association
// lifetime remains bounded and does not pre-allocate 64 native owners.
// 64 cold slots leave headroom for 32 established WBD lanes, reconnections,
// and up to 8 independently bounded ordinary TLS decoy splices.
const (
    originalV4NativeLaneSlots=32
    originalV4ColdAssociationSlots=64
    originalV4MaxDecoySplices=8
)
func originalV4DecoySlots(c config)chan struct{}{
    if c.decoyTarget==""{return nil}
    return make(chan struct{},originalV4MaxDecoySplices)
}
func originalV4ServerDecoy(c config)*realityfront.FallbackConfig{
    if c.decoyTarget==""{return nil}
    return &realityfront.FallbackConfig{
        Target:c.decoyTarget,ServerName:c.serverName,
        DialTimeout:5*time.Second,SessionTimeout:45*time.Second,MaxBytes:64<<20,
    }
}

func runServer(ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,
    leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,
    coldReauth bool,connected *bool)(retErr error){
    if epochs==nil{return realityfront.ErrAdmissionParams}
    if leases!=nil||c.manualClientLease4.IsValid()||len(c.manualClientLeases4)>0{
        return runSharedMultiServer(ctx,c,ifindex,tun,raw,emit,leases,epochs,connected)
    }
    certificate,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    product,err:=realityfront.NewV4LinuxServerProduct(
        realityfront.V4LinuxServerProductConfig{
            Fallback:originalV4ServerDecoy(c),FallbackSlots:originalV4DecoySlots(c),
            Epochs:epochs,NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,
            CleanupOwnedNetwork:productNativeCleanup(c,tun),
            ConfigureTunnelMTU:configureTunnelMTU(c,tun),
            FECMode:c.fecMode,FECProfile:c.fecProfile,DisableOuterRepair:c.disableOuterRepair,
            StartupPaddingMode:c.startupPaddingMode,OuterIPMTU:c.outerMTU,
            PeerPersona:c.peerPersona,Authenticate:originalV4CredentialCheck(c),
        })
    if err!=nil{return err}
    table,err:=faketcp.NewServerAssociationTable(originalV4ColdAssociationSlots,emit)
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
                        if errors.Is(e,realityfront.ErrV4FallbackHandled)||
                           (c.decoyTarget!=""&&(
                            errors.Is(e,realityfront.ErrNotClientHello)||
                            errors.Is(e,realityfront.ErrMalformedHello)||
                            errors.Is(e,realityfront.ErrUnsupportedHello)||
                            errors.Is(e,io.EOF)||errors.Is(e,io.ErrUnexpectedEOF))) {
                            // One ordinary visitor must not exhaust the singleton
                            // cold candidate slot before a real WBD arrival.
                            select{case <-admitted:default:}
                            return
                        }
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
        m,n,b,e:=product.OriginalNormalStartupPaddingCounters()
        logNormalStartupPadding("server",c.fecMode!=realityfront.FecV2Off,m,n,b,e)
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
// Validate a nonzero per-user tunnel ID only after the ORIGINAL protected
// credential authentication, never from pre-TLS address or packet fields.
// Legacy singleton remains exact-ID bound.
// The username+nonzero persistent installation determines an auto tunnel ID,
// never an unauthenticated packet address or caller-chosen manual ID.
func originalV4VerifiedAutoTunnelAfterAuth(req realityfront.AdmissionRequest)error{
 if !req.AutoLease||req.Username==""||len(req.TunnelID)!=16||len(req.InstallationID)!=16{return realityfront.ErrAdmissionParams}
 var install logicaltunnel.InstallationID
 copy(install[:],req.InstallationID)
 if install==[16]byte{}{return realityfront.ErrAdmissionParams}
 id:=logicaltunnel.DerivedTunnelID(req.Username,install)
 if string(req.TunnelID)!=string(id[:]){return realityfront.ErrAdmissionParams}
 return nil
}
func originalV4SharedLeaseRequestAfterAuth(c config,req realityfront.AdmissionRequest,hasPool bool)error{
 if hasPool&&req.AutoLease{return originalV4VerifiedAutoTunnelAfterAuth(req)}
 return originalV4ManualAccountTunnelAfterAuth(c,req)
}
func originalV4ManualAccountTunnelAfterAuth(c config,req realityfront.AdmissionRequest)error{
    // Only a credential-bound roster may assign an existing protected auto
    // lease; a legacy singleton manual /32 still rejects auto admission.
    if len(req.TunnelID)!=16||(req.AutoLease&&len(c.manualClientLeases4)==0){return realityfront.ErrAdmissionParams}
    if len(c.manualClientLeases4)==0{
        if string(req.TunnelID)!=string(c.tunnel[:]){return realityfront.ErrAdmissionParams}
        return nil
    }
    if _,ok:=c.manualClientLeases4[req.Username];!ok{return realityfront.ErrAdmissionParams}
    if req.AutoLease{
        if err:=originalV4VerifiedAutoTunnelAfterAuth(req);err!=nil{return err}
    }
    nonzero:=false
    for _,b:=range req.TunnelID{if b!=0{nonzero=true;break}}
    if !nonzero{return realityfront.ErrAdmissionParams}
    return nil
}
func runSharedMultiServer(
    ctx context.Context,c config,ifindex uint32,tun *ownedTun,
    raw *faketcp.RawIPv4Endpoint,emit faketcp.SegmentEmitter,
    leases *logicaltunnel.LeaseRegistry,epochs *realityfront.V4EpochStore,
    connected *bool,
)(retErr error){
    if epochs==nil||connected==nil||
        (leases==nil&&!c.manualClientLease4.IsValid()&&len(c.manualClientLeases4)==0)||
        (c.manualClientLease4.IsValid()&&(leases!=nil||len(c.manualClientLeases4)>0)){
        return realityfront.ErrAdmissionParams
    }
    trustedManualLease:=""
    if c.manualClientLease4.IsValid(){trustedManualLease=c.manualClientLease4.String()}
    certificate,err:=tls.LoadX509KeyPair(c.tlsCert,c.tlsKey)
    if err!=nil{return err}
    shared,err:=realityfront.NewV4LinuxSharedTun(tun.f,c.tunName)
    if err!=nil{return err}
    decoySlots:=originalV4DecoySlots(c)
    table,err:=faketcp.NewServerAssociationTable(originalV4ColdAssociationSlots,emit)
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
            if err:=originalV4SharedLeaseRequestAfterAuth(c,req,leases!=nil);err!=nil{return err}
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
        // Read original per-session M4 padding before generation Stop,
        // not a process-wide counter or unauthenticated CLI preference.
        if mode,count,padded,e:=rec.product.OriginalNormalStartupPaddingCounters();e==nil{
            if effective,e:=rec.product.OriginalFECReadback();e==nil{
                logNormalStartupPadding("server",effective.Mode!="off",mode,count,padded,nil)
            }
        }
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
        // A shared server may authenticate Windows and independent Linux
        // clients simultaneously. Keep the original wire persona on this
        // single cold association, never reuse a process-wide persona for
        // every Rust RX owner. Unknown SYN remains the explicit CLI default.
        nativePersona,personaKnown:=originalV4ColdAssocPeerPersona(rec.assoc,c.peerPersona)
        cfg:=realityfront.V4LinuxServerProductConfig{
            Fallback:originalV4ServerDecoy(c),FallbackSlots:decoySlots,
            Epochs:epochs,NetworkInterface:c.rawInterface,NetworkIfIndex:ifindex,
            Tun:tun.f,TunName:c.tunName,SharedTun:shared,
            // Only real authenticated auto-lease server sessions reach
            // this path; old manual/standalone duplicate lane stays DENY.
            AllowLaneReplacement:true,
            ManualLease4:trustedManualLease,ManualLeases4:c.manualClientLeases4,
            CleanupOwnedNetwork:productNativeCleanup(c,tun),
            // One authenticated peer cannot mutate a sibling's TUN MTU.
            // The original Rust per-session record/route budgets still apply.
            ConfigureTunnelMTU:nil,
            FECMode:c.fecMode,FECProfile:c.fecProfile,
            // The original TLS policy is this client's owner configuration;
            // server process --mode is not a global FEC admission filter.
            PerClientNormalFEC:true,
            StartupPaddingMode:c.startupPaddingMode,OuterIPMTU:c.outerMTU,
            DisableOuterRepair:c.disableOuterRepair,PeerPersona:nativePersona,
            Authenticate:originalV4CredentialCheck(c),
        }
        p,err:=realityfront.NewV4LinuxServerProduct(cfg)
        if err!=nil{
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=product")
            return
        }
        mu.Lock();rec.product=p;mu.Unlock()
        sess,err:=p.AcceptAuthenticatedPeer(runCtx,rec.assoc,reply)
        if errors.Is(err,realityfront.ErrV4FallbackHandled){return}
        if err!=nil{
            log.Printf("V4_PUBLIC_MULTI_ADMISSION_REJECT stage=original_tls_or_owner")
            return
        }
        log.Printf("V4_PUBLIC_MULTI_PEER_PERSONA role=server incoming=%d cold_syn_known=%t actual_original_TLS_Rust_M4=1",nativePersona,personaKnown)
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
        mu.Unlock()
        // Initial server session publishes its /32 route directly. In an
        // overlap, Rust kept A's exact route: authenticate client B's
        // one-shot cold Health before server B can receive NEW TUN DATA.
        // No registry lock is held across proof polling or native Stop.
        if proofErr:=p.PromoteNormalServerAfterAuthenticatedPeerRx();proofErr!=nil{
            proofErr=waitOriginalNativeServerClientM4Ready(runCtx,
                p.OriginalLoopPulse,p.PromoteNormalServerAfterAuthenticatedPeerRx,
                5*time.Second)
            if proofErr!=nil{
                mu.Lock()
                delete(detached,rec.assoc)
                peers:=peersLocked()
                var restoreErr error
                if len(peers)>0{restoreErr=raw.ExcludeDetachedDataSet(peers)}
                mu.Unlock()
                closeErr:=p.Close()
                log.Printf("V4_PUBLIC_MULTI_SERVER_B_CLIENT_UNPROVEN port=%d old_route_preserved=1 reason=%v",
                    flow.ClientPort,proofErr)
                if restoreErr!=nil||closeErr!=nil{
                    select{case transportErr<-errors.Join(restoreErr,closeErr):default:}
                }
                return
            }
            log.Printf("V4_PUBLIC_MULTI_SERVER_B_CLIENT_READY port=%d source=authenticated_client_native_Health old_route_promoted=1",
                flow.ClientPort)
        }
        mu.Lock()
        if stopping||runCtx.Err()!=nil{
            delete(detached,rec.assoc)
            peers:=peersLocked()
            if len(peers)>0{_ = raw.ExcludeDetachedDataSet(peers)}
            mu.Unlock()
            _=p.Close()
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
    // Cold FakeTCP slots and Rust native lane slots are separate and bounded.
    // A 32-slot cap is not a claim of 32 long-lived qualified users.
    log.Printf("V4_PUBLIC_MULTI_SERVER_READY role=server port=%d cold_association_slots=%d native_owner_slots=%d shared_rust_tun=1 decoy_max_splices=%d",
        c.localPort,originalV4ColdAssociationSlots,originalV4NativeLaneSlots,cap(decoySlots))
    var rawInitialSYNSeen atomic.Bool
    var rawInitialSYNACKSent atomic.Bool
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
                // Observability ONLY: actual original AF_PACKET receiver,
                // syntactic untrusted SYN and MSS, NOT authenticated identity.
                // No packet bytes, addresses or credential material logged.
                if rawInitialSYNSeen.CompareAndSwap(false,true){
                    log.Printf("V4_PUBLIC_ORIGINAL_SERVER_RAW_INITIAL_SYN_RX source=original_af_packet untrusted=1")
                }
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
                if rawInitialSYNACKSent.CompareAndSwap(false,true){
                    log.Printf("V4_PUBLIC_ORIGINAL_SERVER_RAW_SYNACK_TX_OK source=original_af_packet untrusted=1")
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

 // B67 cold OS validation only; Android already owns the translator.
func checkOriginalAndroidCLAT(c config)error{
 if !rootjournal.ValidCLATScope(c.androidClatParent,c.rawInterface,c.androidClatPrefix,c.localIP)||
    c.androidNetworkHandle>>32==0||c.androidNetworkHandle>>32>65535{
    return fmt.Errorf("invalid Android CLAT parent/IPv4/NAT64 scope")
 }
 parent,e:=net.InterfaceByName(c.androidClatParent)
 if e!=nil||parent==nil||parent.Flags&net.FlagUp==0{return fmt.Errorf("Android CLAT parent missing")}
 addresses,e:=parent.Addrs();if e!=nil{return e}
 global:=false
 for _,a:=range addresses{
    p,e:=netip.ParsePrefix(a.String())
    if e==nil&&p.Addr().Is6()&&!p.Addr().Is4In6()&&p.Addr().IsGlobalUnicast(){global=true;break}
 }
 if !global{return fmt.Errorf("Android CLAT parent lost usable IPv6")}
 translated,e:=net.InterfaceByName(c.rawInterface)
 if e!=nil||translated==nil||translated.Flags&net.FlagUp==0{return fmt.Errorf("Android CLAT interface missing")}
 addresses,e=translated.Addrs();if e!=nil{return e}
 for _,a:=range addresses{
    p,e:=netip.ParsePrefix(a.String())
    if e==nil&&p.Bits()==32&&p.Addr()==c.localIP{return nil}
 }
 return fmt.Errorf("Android CLAT IPv4 /32 changed")
}
