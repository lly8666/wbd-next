//go:build windows

package windowsclient

import (
    "context"
    "crypto/rand"
    "encoding/binary"
    "encoding/hex"
    "encoding/json"
    "errors"
    "net"
    "net/netip"
    "os"
    "os/exec"
    "path/filepath"
    "strconv"
    "strings"
    "testing"
    "time"

    "github.com/tailscale/wf"
)
func n4IPv4Checksum(b []byte)uint16{
    var sum uint32
    for i:=0;i<len(b);i+=2{sum+=uint32(binary.BigEndian.Uint16(b[i:i+2]))}
    for sum>>16!=0{sum=(sum&0xffff)+(sum>>16)}
    return ^uint16(sum)
}
func n4MakeKernelUDP(src,dst [4]byte,srcPort,dstPort uint16,payload []byte)[]byte{
    len4:=20+8+len(payload)
    b:=make([]byte,len4)
    b[0]=0x45;b[1]=0
    binary.BigEndian.PutUint16(b[2:4],uint16(len4))
    binary.BigEndian.PutUint16(b[4:6],0x5511)
    binary.BigEndian.PutUint16(b[6:8],0x4000)
    b[8]=64;b[9]=17
    copy(b[12:16],src[:]);copy(b[16:20],dst[:])
    binary.BigEndian.PutUint16(b[10:12],n4IPv4Checksum(b[:20]))
    binary.BigEndian.PutUint16(b[20:22],srcPort)
    binary.BigEndian.PutUint16(b[22:24],dstPort)
    binary.BigEndian.PutUint16(b[24:26],uint16(8+len(payload)))
    copy(b[28:],payload)
    // A complete Windows NDIS/Wintun ingress packet carries a VALID UDP
    // pseudoheader checksum. An IPv4 zero-checksum packet is legal on the
    // wire, but it is not a sufficiently strict native driver qualification.
    checksumInput:=make([]byte,12+8+len(payload))
    copy(checksumInput[0:4],src[:]);copy(checksumInput[4:8],dst[:])
    checksumInput[9]=17
    binary.BigEndian.PutUint16(checksumInput[10:12],uint16(8+len(payload)))
    copy(checksumInput[12:],b[20:])
    if len(checksumInput)%2!=0{checksumInput=append(checksumInput,0)}
    sum:=n4IPv4Checksum(checksumInput)
    if sum==0{sum=0xffff}
    binary.BigEndian.PutUint16(b[26:28],sum)
    return b
}
func containsRuleName(output,name string)bool{
    // A rule's exact user generated display name is the only match.
    // No external config or global firewall state changes allowed.
    for _,line:=range strings.Split(output,"\n"){
        if strings.TrimSpace(line)==name || strings.TrimSpace(line)=="Rule Name: "+name{
            return true
        }
    }
    return false
}
func TestM0PLAN020RealSignedWintunNativeKernelUDPFirstDeliveryStop(t *testing.T){
    if os.Getenv("WBD_M0_PLAN020_REAL_WINTUN_UDP")!="1" ||
       os.Getenv("GITHUB_ACTIONS")!="true"{
        t.Skip("NOT_RUN: this is a real native signed-Wintun hosted Windows2022 app delivery gate")
    }
    receipt:=map[string]string{
        "source_sha":os.Getenv("GITHUB_SHA"),"result":"FAIL_UNFINISHED",
        "owner":"M0_PLAN020","wfp":"TEST_ONLY_FAKE_GUARD_NO_GLOBAL_WFP",
        "route":"NO_DEFAULT_CAPTURE_MUTATION",
        "actual_native_kernel_udp_app":"NOT_RUN",
        "authenticated_original_go_rust_packet":"NOT_RUN",
        "full_windows_public_product":"NOT_QUALIFIED",
    }
    defer func(){
        target:=os.Getenv("WBD_M0_PLAN020_UDP_REPORT")
        if target==""{t.Error("report path required");return}
        p,e:=json.MarshalIndent(receipt,"","  ");if e!=nil{t.Error(e);return}
        if e=os.MkdirAll(filepath.Dir(target),0700);e!=nil{t.Error(e);return}
        if e=os.WriteFile(target,append(p,'\n'),0600);e!=nil{t.Error(e)}
    }()
    if receipt["source_sha"]==""{t.Fatal("missing immutable workflow SOURCE")}
    var nonce [8]byte
    if _,err:=rand.Read(nonce[:]);err!=nil{t.Fatal(err)}
    tun,err:=OpenTUN("WBD-M0-UDP-"+hex.EncodeToString(nonce[:]))
    if err!=nil{
        receipt["result"]="UNSUPPORTED_SIGNED_WINTUN_OR_ADMIN"
        t.Skipf("actual process-created signed native Wintun unavailable: %v",err)
    }
    defer func(){if e:=tun.Close();e!=nil{t.Errorf("native Wintun close: %v",e)}}()
    ctx,cancel:=context.WithTimeout(context.Background(),22*time.Second)
    defer cancel()
    now,err:=tun.NativeIdentity(ctx)
    if err!=nil||!now.CreatedByProcess||now.Index==0||now.LUID==0{
        t.Fatalf("actual native Wintun GUID/LUID/index readback: %+v %v",now,err)
    }
    var install,epoch [16]byte
    if _,err=rand.Read(install[:]);err!=nil{t.Fatal(err)}
    if _,err=rand.Read(epoch[:]);err!=nil{t.Fatal(err)}
    guid,err:=n4NativeInterfaceGUID(now.Index)
    if err!=nil{t.Fatal(err)}
    id:=N4UnifiedIdentity{Installation:install,Generation:epoch,
        WintunLUID:now.LUID,WintunIndex:now.Index,
        WintunGUID:guid.String(),AdapterAlias:tun.Name()}
    pin,err:=n4ProbeOriginalWintunPnP(ctx,id)
    if err!=nil{t.Fatalf("signed Wintun native PnP identity: %v",err)}
    id.PnPInstanceSHA256=pin.InstanceSHA256
    if !n4ValidPinnedPnPHash(id.PnPInstanceSHA256){t.Fatal("not pinned original PnP identity")}
    driver,err:=n4CreateOriginalKernelPacketLease(ctx,tun,id)
    if err!=nil{t.Fatal(err)}
    foreign:=id;foreign.Generation[0]^=1
    if _,err:=n4CreateOriginalKernelPacketLease(ctx,tun,foreign);err==nil{
        t.Fatal("foreign original generation adopted live ring")
    }
    if _,err:=driver.n4DeliverAuthenticatedIPv4(ctx,[]byte{4,1,2});!errors.Is(err,ErrInvalidBinding){
        t.Fatalf("invalid original packet was copied: %v",err)
    }
    // One fresh test-only local /32, never host default route. Real native
    // IP Helper CreateUnicast and DAD readback; fake test guard cannot grant
    // product WFP or applied status.
    lease:=N4NativeLeaseIntent{InterfaceIndex:now.Index,
        Prefix:netip.MustParsePrefix("198.18.20.77/32")}
    writer:=N4WindowsLeaseWriter{
        Guard:&n4FakeGuard{durable:true,active:true},
        Adapter:tun,Snapshot:N4WindowsAddressSnapshot{},
    }
    token,err:=writer.Create(ctx,lease)
    if err!=nil{t.Fatalf("real original native Wintun IPv4 IP Helper lease: %v",err)}
    defer func(){
        cleanup,done:=context.WithTimeout(context.Background(),10*time.Second)
        defer done()
        if e:=writer.DeleteConfirmed(cleanup,token);e!=nil{t.Errorf("exact owned /32 IP cleanup FAILED: %v",e)}
    }()
    for{
        row,found,e:=(N4WindowsLeaseReader{}).Lookup(ctx,lease)
        if e!=nil{t.Fatal(e)}
        if found && N4NativeLeaseDADGate(row,lease)==nil{break}
        if ctx.Err()!=nil{t.Fatalf("OS /32 not DAD preferred: %v",ctx.Err())}
        time.Sleep(100*time.Millisecond)
    }
    // Force the application socket to the verified DAD-preferred IPv4
    // address on THIS process-created signed Wintun, not any host NIC.
    sock,err:=net.ListenUDP("udp4",&net.UDPAddr{
        IP:net.IPv4(198,18,20,77),Port:0,
    })
    if err!=nil{t.Fatal(err)}
    defer sock.Close()
    destPort:=uint16(sock.LocalAddr().(*net.UDPAddr).Port)
    // DIAGNOSTIC ONLY. A Windows runner may classify its newly-created
    // Wintun as Public and Windows Defender drops unsolicited incoming
    // UDP before the bound socket. Install only one unique ephemeral,
    // exact-source/exact-destination/exact-port ALLOW, never disable a
    // firewall profile, never change default route, never promote the
    // temporary rule to N4's persistent owned product WFP guard.
    // No process production file imports exec/netsh; this is _test only.
    narrowRule:="WBD-M0-TEST-UDP-"+hex.EncodeToString(nonce[:])
    addArgs:=[]string{"advfirewall","firewall","add","rule",
        "name="+narrowRule,"dir=in","action=allow","enable=yes",
        "protocol=UDP","localip=198.18.20.77","remoteip=198.18.20.88",
        "localport="+strconv.Itoa(int(destPort)),"profile=any"}
    firewallOut,firewallErr:=exec.CommandContext(ctx,"netsh",addArgs...).CombinedOutput()
    if firewallErr!=nil{
        t.Fatalf("cannot install exact ephemeral native WFP/Defender test port permission (no fallback): %v output=%q",
            firewallErr,string(firewallOut))
    }
    t.Log("M0_PLAN020_TEST_ONLY_EXACT_WINDOWS_DEFENDER_UDP_ALLOW",
        narrowRule,"local=198.18.20.77",destPort,"remote=198.18.20.88")
    defer func(){
        cleanup,done:=context.WithTimeout(context.Background(),10*time.Second)
        defer done()
        deleted,outErr:=exec.CommandContext(cleanup,"netsh","advfirewall",
            "firewall","delete","rule","name="+narrowRule).CombinedOutput()
        if outErr!=nil{
            t.Errorf("test-only narrow Windows Defender rule not deleted; no OS cleanup receipt: %v output=%q",outErr,string(deleted))
            return
        }
        verify,err:=exec.CommandContext(cleanup,"netsh","advfirewall",
            "firewall","show","rule","name="+narrowRule).CombinedOutput()
        if err==nil && (len(verify)==0 || !errors.Is(err,exec.ErrNotFound)){
            // netsh frequently exits 0 for 'No rules match', so look for
            // unique rule name rather than assuming the exit status.
            if string(verify)!="" && containsRuleName(string(verify),narrowRule){
                t.Errorf("test-only WFP rule survived deletion: %s",narrowRule)
            }
        }
    }()
    // Real WFP persistent engine in the SAME created native Wintun
    // generation as the kernel UDP app. This is a second, independently
    // qualified dimension. The one block is limited to reserved TEST-NET-3
    // 203.0.113.254:65530, not host-wide DNS/IPv6/default-route capture.
    // Use the very same exact-owned native WFP ARM + CAS/Disarm code that
    // the M4 product backend consumes; do not treat this as global Applied.
    sid:=wf.SublayerID(n4WFPTestGUID(t))
    rid:=wf.RuleID(n4WFPTestGUID(t))
    sub:=&wf.Sublayer{
        ID:sid,Name:"WBD M0 PLAN020 native Wintun same-owner WFP limited",
        Persistent:true,Weight:11,
    }
    narrowWfpRule:=&wf.Rule{
        ID:rid,Name:"WBD M0 PLAN020 guarded TEST-NET-3 limited",
        Layer:wf.LayerALEAuthConnectV4,Sublayer:sid,Weight:1,
        Persistent:true,Action:wf.ActionBlock,
        Conditions:[]*wf.Match{
            {Field:wf.FieldIPRemoteAddress,Op:wf.MatchTypeEqual,
                Value:netip.MustParseAddr("203.0.113.254")},
            {Field:wf.FieldIPRemotePort,Op:wf.MatchTypeEqual,
                Value:uint16(65530)},
        },
    }
    wfpPlan:=n4WFPRulePlan{Sublayer:sub,Rules:[]*wf.Rule{narrowWfpRule}}
    if err:=n4WFPArmExactPlan(ctx,wfpPlan);err!=nil{
        t.Fatalf("real bounded WFP persistent same native Wintun generation ARM: %v",err)
    }
    wfpArmed:=true
    defer func(){
        if !wfpArmed{return}
        cleanup,done:=context.WithTimeout(context.Background(),10*time.Second)
        defer done()
        if e:=n4WFPDisarmExactPlan(cleanup,wfpPlan,false);e!=nil{
            t.Errorf("real persistent WFP TEST-NET owned exact CAS cleanup failure: %v",e)
        }
    }()
    check,e:=wf.New(&wf.Options{Dynamic:false})
    if e!=nil{t.Fatal(e)}
    present,matching,e:=n4WFPReadOwned(check,wfpPlan)
    closeErr:=check.Close()
    if e!=nil||closeErr!=nil||!present||!matching[rid]{
        t.Fatalf("independent WFP engine did not read persistent live generation rule: sub=%v rule=%v err=%v close=%v",
            present,matching[rid],e,closeErr)
    }
    tampered:=*narrowWfpRule
    tampered.Name="foreign replacement of native owned WFP rule"
    if e:=n4WFPDisarmExactPlan(ctx,n4WFPRulePlan{
        Sublayer:sub,Rules:[]*wf.Rule{&tampered},
    },false);!errors.Is(e,ErrN4ForeignRoute){
        t.Fatalf("foreign WFP deletion was not independently refused: %v",e)
    }
    t.Log("M0_PLAN020_SAME_NATIVE_WINTUN_WFP_PERSISTENT_TEST_NET_OWNED_CAS_PASS")
    // Native IP Helper route exercised on the very same signed Wintun
    // while its real WFP TEST-NET guard is persistent. This is ONE safe
    // reserved destination /32, NEVER a host default, split /1 route, or
    // synthetic in-memory route backend. Exact CAS denial must leave
    // the OS entry untouched before owned Stop.
    route:=NativeRouteKey{
        Prefix:netip.MustParsePrefix("203.0.113.251/32"),
        Interface:now.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:5,
    }
    backend:=N4WindowsRouteBackend{}
    already,_,e:=backend.Lookup(ctx,route)
    if e!=nil||already{
        t.Fatalf("TEST-NET route preflight already owned/foreign: present=%v err=%v",already,e)
    }
    if e:=backend.CreateIfAbsent(ctx,route);e!=nil{
        t.Fatalf("real Windows native IP Helper isolated Wintun route creation: %v",e)
    }
    routeOwned:=true
    defer func(){
        if !routeOwned{return}
        cleanup,done:=context.WithTimeout(context.Background(),10*time.Second)
        defer done()
        if e:=backend.RemoveOwned(cleanup,route);e!=nil{
            t.Errorf("native exact-owned TEST-NET route CAS cleanup failed: %v",e)
        }
    }()
    has,exact,e:=backend.Lookup(ctx,route)
    if e!=nil||!has||!exact{
        t.Fatalf("real Windows IP Helper route OS readback missing/mismatch: %v %v %v",has,exact,e)
    }
    foreignRoute:=route
    foreignRoute.Metric=route.Metric+1
    if e:=backend.RemoveOwned(ctx,foreignRoute);!errors.Is(e,ErrN4ForeignRoute){
        t.Fatalf("forged metric deleted original route: %v",e)
    }
    if has,exact,e=backend.Lookup(ctx,route);e!=nil||!has||!exact{
        t.Fatalf("foreign route CAS changed genuine exact-owned Windows route: %v %v %v",has,exact,e)
    }
    if e:=backend.RemoveOwned(ctx,route);e!=nil{
        t.Fatalf("real Windows route Stop/RemoveOwned after WFP readback: %v",e)
    }
    routeOwned=false
    if has,_,e=backend.Lookup(ctx,route);e!=nil||has{
        t.Fatalf("real Windows route removal did not verify absent: %v %v",has,e)
    }
    t.Log("M0_PLAN020_SAME_WINTUN_NATIVE_ROUTE_IP_HELPER_CAS_TEST_NET_PASS")
    app:=[]byte("M0-PLAN020-actual-Windows-IP-helper-kernel-udp-first-app")
    packet:=n4MakeKernelUDP([4]byte{198,18,20,88},[4]byte{198,18,20,77},
        41131,destPort,app)
    if n,err:=driver.n4DeliverAuthenticatedIPv4(ctx,packet);err!=nil||n!=len(packet){
        t.Fatalf("real signed WintunSendPacket kernel copy: %d %v",n,err)
    }
    if err:=sock.SetReadDeadline(time.Now().Add(4*time.Second));err!=nil{t.Fatal(err)}
    out:=make([]byte,2048)
    n,from,err:=sock.ReadFromUDP(out)
    if err!=nil{
        native,callErr:=exec.Command("netstat","-s","-p","udp").CombinedOutput()
        t.Logf("M0_PLAN020_WINDOWS_UDP_KERNEL_NETSTACK_RECEIVE_DIAG error=%v netstat_error=%v counters=%q",
            err,callErr,string(native))
        t.Fatalf("actual Windows UDP socket missed Wintun ring injected IPv4 even after exact narrow test-only Defender permit: %v",err)
    }
    if n!=len(app)||string(out[:n])!=string(app)||from==nil||
       !from.IP.Equal(net.ParseIP("198.18.20.88")){
        t.Fatalf("actual Windows UDP app payload/source mismatch len=%d",n)
    }
    // Reverse ACTUAL Windows UDP socket -> the same signed Wintun native
    // receive ring. A separately owned single TEST-NET /32 route forces
    // egress onto THIS generation's OS ifindex; the normal host default
    // route, DNS, IPv6 and production WFP remain entirely untouched.
    reverseRoute:=NativeRouteKey{
        Prefix:netip.MustParsePrefix("198.18.20.88/32"),
        Interface:now.Index,NextHop:netip.MustParseAddr("0.0.0.0"),Metric:7,
    }
    reverseHas,_,reverseErr:=backend.Lookup(ctx,reverseRoute)
    if reverseErr!=nil||reverseHas{
        t.Fatalf("reverse actual Win32 route preflight foreign/present: %v %v",reverseHas,reverseErr)
    }
    if reverseErr=backend.CreateIfAbsent(ctx,reverseRoute);reverseErr!=nil{
        t.Fatalf("reverse same signed Wintun native route create failed: %v",reverseErr)
    }
    reverseOwned:=true
    defer func(){
        if !reverseOwned{return}
        cleanup,done:=context.WithTimeout(context.Background(),10*time.Second)
        defer done()
        if e:=backend.RemoveOwned(cleanup,reverseRoute);e!=nil{
            t.Errorf("reverse native IP Helper /32 exact CAS cleanup failure: %v",e)
        }
    }()
    reverseHas,reverseExact,reverseErr:=backend.Lookup(ctx,reverseRoute)
    if reverseErr!=nil||!reverseHas||!reverseExact{
        t.Fatalf("reverse actual IP Helper Wintun /32 readback failed: %v %v %v",reverseHas,reverseExact,reverseErr)
    }
    reverseApp:=[]byte("M0-PLAN020-real-Windows-UDP-socket-to-Wintun-reverse-ring")
    reverseDest:=&net.UDPAddr{IP:net.IPv4(198,18,20,88),Port:41132}
    sent,sendErr:=sock.WriteToUDP(reverseApp,reverseDest)
    if sendErr!=nil||sent!=len(reverseApp){
        t.Fatalf("Windows kernel socket reverse UDP send failed: %d %v",sent,sendErr)
    }
    ring:=make([]byte,65535)
    reverseObserved:=false
    // Bounded nonblocking ring polls: never hold the lease while sleeping,
    // and do not convert no-packet into a fabricated successful reply.
    until:=time.Now().Add(4*time.Second)
    for time.Now().Before(until){
        size,readErr:=driver.n4ReceiveReadyIPv4(ctx,ring)
        if errors.Is(readErr,ErrN4NativeNoPacket){
            time.Sleep(10*time.Millisecond)
            continue
        }
        if readErr!=nil{t.Fatalf("actual Wintun reverse packet ring read: %v",readErr)}
        frame:=ring[:size]
        if size<28 || frame[0]>>4!=4{continue}
        ihl:=int(frame[0]&0x0f)*4
        if ihl<20||size<ihl+8||frame[9]!=17{continue}
        if !net.IP(frame[12:16]).Equal(net.IPv4(198,18,20,77)) ||
           !net.IP(frame[16:20]).Equal(net.IPv4(198,18,20,88)) ||
           binary.BigEndian.Uint16(frame[ihl:ihl+2])!=destPort ||
           binary.BigEndian.Uint16(frame[ihl+2:ihl+4])!=41132{continue}
        udpLen:=int(binary.BigEndian.Uint16(frame[ihl+4:ihl+6]))
        if udpLen!=8+len(reverseApp)||size<ihl+udpLen||
           string(frame[ihl+8:ihl+udpLen])!=string(reverseApp){continue}
        reverseObserved=true
        break
    }
    if !reverseObserved{
        t.Fatal("real Windows UDP socket send did NOT appear on SAME signed Wintun reverse native receive ring")
    }
    if e:=backend.RemoveOwned(ctx,reverseRoute);e!=nil{
        t.Fatalf("reverse TEST-NET /32 owned OS route CAS removal: %v",e)
    }
    reverseOwned=false
    if exists,_,e:=backend.Lookup(ctx,reverseRoute);e!=nil||exists{
        t.Fatalf("reverse route survived owned deletion: %v %v",exists,e)
    }
    t.Log("M0_PLAN020_REAL_SIGNED_WINTUN_ACTUAL_WINDOWS_UDP_SOCKET_REVERSE_RING_PASS")
    if err:=driver.Stop(ctx);err!=nil{t.Fatal(err)}
    if err:=driver.Stop(ctx);err!=nil{t.Fatal("repeat Stop",err)}
    if _,err:=driver.n4DeliverAuthenticatedIPv4(ctx,packet);!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("stale generation wrote to real kernel: %v",err)
    }
    if _,err:=driver.n4ReceiveReadyIPv4(ctx,out);!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("stale generation read real kernel: %v",err)
    }
    counts,err:=driver.Counts()
    if err!=nil||!counts.Stopped||counts.KernelCopied!=1||counts.KernelReceived<1||counts.Rejected<1{
        t.Fatalf("inaccurate actual native kernel counters %+v %v",counts,err)
    }
    receipt["actual_native_kernel_udp_app"]="PASS_SIGNED_WINTUN_KERNEL_COPY_TO_REAL_WINDOWS_UDP_SOCKET"
    receipt["native_test_only_firewall_rule"]="EXACT_UDP_SRC_DST_PORT_EPHEMERAL_ALLOW_REMOVED_ON_STOP_NOT_PRODUCT_WFP"
    receipt["native_same_wintun_persistent_WFP"]="PASS_REAL_EXACT_TEST_NET_RULE_FOREIGN_REJECTED_CAS_REMOVED_AFTER_SESSION_NOT_GLOBAL_CAPTURE"
    receipt["native_same_wintun_IP_Helper_route"]="PASS_REAL_ONE_TEST_NET_32_OS_READBACK_FOREIGN_METRIC_DENIED_EXACT_CAS_DELETE_NO_DEFAULT_ROUTE"
    receipt["signed_adapter"]="PASS_CREATED_GUID_LUID_IFINDEX_PNP_PIN"
    receipt["reverse_actual_windows_udp_to_same_signed_wintun_ring"]="PASS_REAL_SOCKET_TO_WINTUN_RECEIVE_PACKET_NO_AEAD"
    receipt["native_reverse_route"]="PASS_TEST_NET_32_EXACT_OS_CAS_REMOVED"
    receipt["native_stop"]="PASS_BOUNDED_NO_WAIT_STALE_DENIED"
    receipt["result"]="PASS_SCOPED_REAL_WIN_KERNEL_BIDIRECTIONAL_UDP_NO_CREDENTIAL_OWNER"
    t.Log("M0_PLAN020_REAL_SIGNED_WINTUN_TO_ACTUAL_WINDOWS_UDP_APPLICATION_PASS kernel_copy=1 app=1 reverse_ring=1 stale_denied=1 real_scoped_WFP_persistent=1 full_global_WFP_NOT_RUN=1")
}

func TestM0WindowsOriginalN4RingOneSecondOSAuditWithImmediateStopFence(t *testing.T){
 now:=time.Now()
 if !n4RealOriginalWintunAuditDue(time.Time{},now)||
    n4RealOriginalWintunAuditDue(now,now.Add(999*time.Millisecond))||
    !n4RealOriginalWintunAuditDue(now,now.Add(time.Second))||
    !n4RealOriginalWintunAuditDue(now,now.Add(-time.Millisecond)){
  t.Fatal("real native PnP identity verification has unbounded/stale refresh")
 }
 // An expired or stopped original native ring cannot use a recent OS
 // audit to bypass generation exclusion, even before one second passes.
 d:=&N4OriginalKernelPacketLease{
  stopped:true,lastVerifiedAt:now,
 }
 if err:=d.check(context.Background());!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("owned Stop fence was skipped: %v",err)
 }
 d.stopped=false
 d.identityRevoked=true
 if err:=d.check(context.Background());!errors.Is(err,ErrN4NativeGuard){
  t.Fatalf("external OS identity rejection was not sticky: %v",err)
 }
}
