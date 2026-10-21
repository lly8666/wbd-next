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
    "path/filepath"
    "testing"
    "time"
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
    app:=[]byte("M0-PLAN020-actual-Windows-IP-helper-kernel-udp-first-app")
    packet:=n4MakeKernelUDP([4]byte{198,18,20,88},[4]byte{198,18,20,77},
        41131,destPort,app)
    if n,err:=driver.n4DeliverAuthenticatedIPv4(ctx,packet);err!=nil||n!=len(packet){
        t.Fatalf("real signed WintunSendPacket kernel copy: %d %v",n,err)
    }
    if err:=sock.SetReadDeadline(time.Now().Add(4*time.Second));err!=nil{t.Fatal(err)}
    out:=make([]byte,2048)
    n,from,err:=sock.ReadFromUDP(out)
    if err!=nil{t.Fatalf("actual Windows UDP socket missed Wintun ring injected IPv4: %v",err)}
    if n!=len(app)||string(out[:n])!=string(app)||from==nil||
       !from.IP.Equal(net.ParseIP("198.18.20.88")){
        t.Fatalf("actual Windows UDP app payload/source mismatch len=%d",n)
    }
    if err:=driver.Stop(ctx);err!=nil{t.Fatal(err)}
    if err:=driver.Stop(ctx);err!=nil{t.Fatal("repeat Stop",err)}
    if _,err:=driver.n4DeliverAuthenticatedIPv4(ctx,packet);!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("stale generation wrote to real kernel: %v",err)
    }
    if _,err:=driver.n4ReceiveReadyIPv4(ctx,out);!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("stale generation read real kernel: %v",err)
    }
    counts,err:=driver.Counts()
    if err!=nil||!counts.Stopped||counts.KernelCopied!=1||counts.Rejected!=1{
        t.Fatalf("inaccurate actual native kernel counters %+v %v",counts,err)
    }
    receipt["actual_native_kernel_udp_app"]="PASS_SIGNED_WINTUN_KERNEL_COPY_TO_REAL_WINDOWS_UDP_SOCKET"
    receipt["signed_adapter"]="PASS_CREATED_GUID_LUID_IFINDEX_PNP_PIN"
    receipt["native_stop"]="PASS_BOUNDED_NO_WAIT_STALE_DENIED"
    receipt["result"]="PASS_SCOPED_REAL_WIN_KERNEL_UDP_FIRST_APP_NO_CREDENTIAL_OWNER_CONNECTED"
    t.Log("M0_PLAN020_REAL_SIGNED_WINTUN_TO_ACTUAL_WINDOWS_UDP_APPLICATION_PASS kernel_copy=1 app=1 stale_denied=1 fake_wfp_test_only=1")
}
