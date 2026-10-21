//go:build windows && wbd_v4_embedded_go
package windowsownerlease

// One real original Go protected credential V4 TLS client/server pair,
// authenticated native Windows M1/M3 Rust client owner and SAME-process
// M4-created-Wintun native Hold/Stop, if the runner actually has its driver.
// This is NOT a Windows route/WFP/GUI kernel application success test.
import (
    "context"
    "crypto/ecdsa"
    "crypto/elliptic"
    "crypto/rand"
    "crypto/tls"
    "crypto/x509"
    "crypto/x509/pkix"
    "encoding/binary"
    "encoding/hex"
    "errors"
    "fmt"
    "math/big"
    "net"
    "net/netip"
    "os"
    "os/exec"
    "strconv"
    "strings"
    "path/filepath"
    "testing"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
    "github.com/lly8666/wobuzhidao/internal/windowsclient"
)

// Test-only Wintun /32 DAD IP Helper lease witness. It is NOT a
// crash-persistent host WFP guard: Arm/Disarm intentionally fail closed.
// Verify only authorizes one bounded address to an ALREADY process-owned
// adapter in this native test, never a default route or public product.
type m0NativeTLSTestGuard struct{}
func (m0NativeTLSTestGuard) Durable()bool{return true}
func (m0NativeTLSTestGuard) Verify(ctx context.Context)(bool,error){
    if err:=ctx.Err();err!=nil{return false,err}
    return true,nil
}
func (m0NativeTLSTestGuard) Arm(context.Context)error{return windowsclient.ErrN4NativeGuard}
func (m0NativeTLSTestGuard) Disarm(context.Context)error{return windowsclient.ErrN4NativeGuard}

func m0RealWintunHeaderChecksum(b []byte)uint16{
    var sum uint32
    for i:=0;i<len(b);i+=2{sum+=uint32(binary.BigEndian.Uint16(b[i:i+2]))}
    for sum>>16!=0{sum=(sum&65535)+(sum>>16)}
    return ^uint16(sum)
}
func m0OriginalTLSRustAEADKernelUDP(payload []byte,dstPort uint16)[]byte{
    total:=20+8+len(payload)
    frame:=make([]byte,total)
    frame[0]=0x45
    binary.BigEndian.PutUint16(frame[2:4],uint16(total))
    binary.BigEndian.PutUint16(frame[4:6],0x5512)
    binary.BigEndian.PutUint16(frame[6:8],0x4000)
    frame[8]=64;frame[9]=17
    copy(frame[12:16],[]byte{198,18,30,88})
    copy(frame[16:20],[]byte{198,18,30,77})
    binary.BigEndian.PutUint16(frame[10:12],m0RealWintunHeaderChecksum(frame[:20]))
    binary.BigEndian.PutUint16(frame[20:22],41131)
    binary.BigEndian.PutUint16(frame[22:24],dstPort)
    binary.BigEndian.PutUint16(frame[24:26],uint16(8+len(payload)))
    copy(frame[28:],payload)
    pseudo:=make([]byte,12+8+len(payload))
    copy(pseudo[:4],frame[12:16]);copy(pseudo[4:8],frame[16:20])
    pseudo[9]=17
    binary.BigEndian.PutUint16(pseudo[10:12],uint16(8+len(payload)))
    copy(pseudo[12:],frame[20:])
    if len(pseudo)%2!=0{pseudo=append(pseudo,0)}
    checksum:=m0RealWintunHeaderChecksum(pseudo)
    if checksum==0{checksum=65535}
    binary.BigEndian.PutUint16(frame[26:28],checksum)
    return frame
}

// The bytes crossing THIS actual signed Windows Wintun kernel ingress
// are the immutable record from original Go credential TLS -> Rust M1/M3,
// not a packet assembled by a synthetic/test-only AEAD sealer. The receiving
// OS socket sees exact ciphertext, NEVER claims peer M3 decrypt/product.
func m0RealOriginalTLSRustAEADToSignedWintunKernelApp(
    t *testing.T,ctx context.Context,tun *windowsclient.TUN,wire []byte,
)[]byte{
    t.Helper()
    if tun==nil||len(wire)<51||len(wire)>543{
        t.Fatal("no valid real Rust M3 ciphertext for native Wintun")
    }
    identity,err:=tun.NativeIdentity(ctx)
    if err!=nil||!identity.CreatedByProcess||identity.Index==0||identity.LUID==0{
        t.Fatalf("original signed Wintun native device identity missing: %+v %v",identity,err)
    }
    lease:=windowsclient.N4NativeLeaseIntent{
        InterfaceIndex:identity.Index,
        Prefix:netip.MustParsePrefix("198.18.30.77/32"),
    }
    writer:=windowsclient.N4WindowsLeaseWriter{
        Guard:m0NativeTLSTestGuard{},Adapter:tun,
        Snapshot:windowsclient.N4WindowsAddressSnapshot{},
    }
    token,err:=writer.Create(ctx,lease)
    if err!=nil{t.Fatalf("exact test-only OS IPv4 /32 lease refused: %v",err)}
    defer func(){
        cleanup,cancel:=context.WithTimeout(context.Background(),10*time.Second)
        defer cancel()
        if e:=writer.DeleteConfirmed(cleanup,token);e!=nil{
            t.Errorf("real test-only original TLS Rust signed Wintun /32 lease not cleaned: %v",e)
        }
    }()
    for{
        row,present,e:=(windowsclient.N4WindowsLeaseReader{}).Lookup(ctx,lease)
        if e!=nil{t.Fatalf("original signed Wintun address independent OS readback: %v",e)}
        if present&&windowsclient.N4NativeLeaseDADGate(row,lease)==nil{break}
        if e=ctx.Err();e!=nil{t.Fatalf("original signed Wintun DAD did not reach preferred: %v",e)}
        time.Sleep(100*time.Millisecond)
    }
    socket,err:=net.ListenUDP("udp4",&net.UDPAddr{IP:net.IPv4(198,18,30,77)})
    if err!=nil{t.Fatalf("OS UDP4 app failed to bind original Wintun address: %v",err)}
    defer socket.Close()
    destPort:=uint16(socket.LocalAddr().(*net.UDPAddr).Port)
    var nonce [8]byte
    if _,err=rand.Read(nonce[:]);err!=nil{t.Fatal(err)}
    rule:="WBD-M0-TLS-RUST-"+hex.EncodeToString(nonce[:])
    args:=[]string{"advfirewall","firewall","add","rule","name="+rule,
        "dir=in","action=allow","enable=yes","protocol=UDP",
        "localip=198.18.30.77","remoteip=198.18.30.88",
        "localport="+strconv.Itoa(int(destPort)),"profile=any"}
    output,err:=exec.CommandContext(ctx,"netsh",args...).CombinedOutput()
    if err!=nil{t.Fatalf("test-only exact Windows Defender permit refused %v: %q",err,output)}
    defer func(){
        cleanup,cancel:=context.WithTimeout(context.Background(),10*time.Second)
        defer cancel()
        deleted,e:=exec.CommandContext(cleanup,"netsh","advfirewall","firewall",
            "delete","rule","name="+rule).CombinedOutput()
        if e!=nil{t.Errorf("test-only rule not deleted %v: %q",e,deleted);return}
        got,e:=exec.CommandContext(cleanup,"netsh","advfirewall","firewall",
            "show","rule","name="+rule).CombinedOutput()
        if e==nil&&strings.Contains(string(got),rule){
            t.Errorf("test-only per-port Defender permit persists: %s",rule)
        }
    }()
    frame:=m0OriginalTLSRustAEADKernelUDP(wire,destPort)
    copied,e:=tun.WritePacket(frame)
    if e!=nil||copied!=len(frame){
        t.Fatalf("actual signed Wintun kernel M3 ciphertext injection FAILED bytes=%d err=%v",copied,e)
    }
    if e=socket.SetReadDeadline(time.Now().Add(4*time.Second));e!=nil{t.Fatal(e)}
    buffer:=make([]byte,2048)
    size,src,e:=socket.ReadFromUDP(buffer)
    if e!=nil||size!=len(wire)||src==nil||
        !src.IP.Equal(net.IPv4(198,18,30,88))||src.Port!=41131||
        string(buffer[:size])!=string(wire){
        t.Fatalf("real signed Wintun kernel app ciphertext source/payload FAILED: size=%d src=%v err=%v",size,src,e)
    }
    t.Log("M0_PLAN020_REAL_ORIGINAL_GO_CREDENTIAL_TLS_RUST_M3_AEAD_SIGNED_WINTUN_KERNEL_TO_ACTUAL_UDP_APP_PASS original_rust_ciphertext=1 exact_OS_app=1 signed_Wintun_lease=1 host_global_WFP_NOT_RUN=1")
    return append([]byte(nil),buffer[:size]...)
}

func m0WinJoinCert(t *testing.T)tls.Certificate{
    t.Helper()
    key,e:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader);if e!=nil{t.Fatal(e)}
    now:=time.Now()
    cert:=&x509.Certificate{
        SerialNumber:big.NewInt(2026),Subject:pkix.Name{CommonName:"target.test"},
        NotBefore:now.Add(-time.Hour),NotAfter:now.Add(time.Hour),
        DNSNames:[]string{"target.test"},KeyUsage:x509.KeyUsageDigitalSignature,
        ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
    }
    der,e:=x509.CreateCertificate(rand.Reader,cert,cert,&key.PublicKey,key)
    if e!=nil{t.Fatal(e)}
    return tls.Certificate{Certificate:[][]byte{der},PrivateKey:key}
}
func TestM0WindowsRealOriginalGoTLSRustM4CreatedWintunSameGeneration(t *testing.T){
    library:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
    if library==""{t.Fatal("pinned source real Windows Rust owner DLL missing")}
    ctx,cancel:=context.WithTimeout(context.Background(),28*time.Second)
    defer cancel()
    routeKey:=[]byte("0123456789abcdef0123456789abcdef")
    flow:=faketcp.ClientFlow{LocalIP:[4]byte{10,78,0,2},
        PeerIP:[4]byte{10,78,0,1},LocalPort:41501,PeerPort:443}
    toServer:=make(chan faketcp.Segment,4096)
    toClient:=make(chan faketcp.Segment,4096)
    emit:=func(out chan<- faketcp.Segment)faketcp.SegmentEmitter{
        return func(seg faketcp.Segment)error{
            seg.Payload=append([]byte(nil),seg.Payload...)
            select{case out<-seg:return nil
            default:return errors.New("bounded Go TCP segment channel full")}
        }
    }
    client,e:=faketcp.NewClientAssociation(flow,123456,time.Second,emit(toServer))
    if e!=nil{t.Fatal(e)}
    defer client.Close()
    if e=client.Start(time.Now());e!=nil{t.Fatal(e)}
    syn:=<-toServer
    server,e:=faketcp.NewServerAssociation(syn,31337,time.Second,emit(toClient))
    if e!=nil{t.Fatal(e)}
    defer server.Close()
    synack,e:=server.SYNACKSegment()
    if e!=nil{t.Fatal(e)}
    if e=client.HandleSegment(synack,time.Now());e!=nil{t.Fatal(e)}
    ack:=<-toServer
    if _,e=server.HandleSegment(ack,time.Now());e!=nil{t.Fatal(e)}
    routerDone:=make(chan struct{})
    defer close(routerDone)
    routerErr:=make(chan error,1)
    sendErr:=func(err error){if err!=nil{select{case routerErr<-err:default:}}}
    go func(){
        for{
            select{
            case <-routerDone:return
            case seg:=<-toServer:
                got,err:=server.HandleSegment(seg,time.Now())
                if err!=nil{sendErr(err);return}
                if got.AckNeeded{sendErr(emit(toClient)(server.ACKSegment(got.Ack)))}
            case seg:=<-toClient:
                if err:=client.HandleSegment(seg,time.Now());err!=nil{
                    sendErr(err);return
                }
            }
        }
    }()
    store,e:=realityfront.NewV4EpochStore(1)
    if e!=nil{t.Fatal(e)}
    type response struct{
        session *realityfront.V4ServerSession
        owner *realityfront.V4WindowsAuthenticatedServerOwner
        err error
    }
    answer:=make(chan response,1)
    go func(){
        peer,session,err:=realityfront.V4WindowsEstablishOriginalServerOwner(
            ctx,library,server,
            realityfront.ServerAdmissionConfig{
                TLS:realityfront.ServerConfig{
                    ServerName:"target.test",RouteKey:routeKey,
                    TLSConfig:&tls.Config{Certificates:[]tls.Certificate{m0WinJoinCert(t)}},
                    Timeout:5*time.Second,
                },
                ExpectedUsername:"protected-owner",ExpectedPassword:"secret",
                ServerLimit:1400,
            },realityfront.V4ServerOptions{DataPlaneReady:true,Epochs:store})
        answer<-response{session:session,owner:peer,err:err}
    }()
    policy,e:=realityfront.FixedPolicyForClient(1,0)
    if e!=nil{t.Fatal(e)}
    native,cliSession,err:=realityfront.V4WindowsEstablishOriginalClientOwner(
        ctx,library,client,realityfront.ClientAdmissionConfig{
            TLS:realityfront.ClientConfig{ServerName:"target.test",
                RouteKey:routeKey,Timeout:5*time.Second},
            Username:"protected-owner",Password:"secret",
            TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,
            LaneID:1,DesiredLanes:1,Policy:policy,
        })
    var resp response
    select{
    case resp=<-answer:
    case <-ctx.Done():t.Fatalf("same-source original Go TLS server timeout: %v",ctx.Err())
    }
    if err!=nil||resp.err!=nil||native==nil||cliSession==nil||resp.session==nil||resp.owner==nil{
        var transportErr error
        select{case transportErr=<-routerErr:default:}
        t.Fatalf("original Go FakeTCP TLS to actual Rust owner failed client=%v server=%v transport=%v",
            err,resp.err,transportErr)
    }
    readback,e:=native.OriginalOwnerReadback()
    if e!=nil||!readback.OwnerActive||readback.DeviceBound||
        readback.ProductApplied||readback.Generation==0{
        t.Fatalf("original native Rust TLS active owner false APPLIED: %+v err=%v",readback,e)
    }
    installed:=false
    if os.Getenv("WBD_M0_TRY_SCOPED_NATIVE_WINTUN")=="1" && m0NativeWintunAvailable(t){
        name:=fmt.Sprintf("WBD-M0-OWNER-%s",os.Getenv("GITHUB_RUN_ID"))
        tun,e:=windowsclient.OpenTUN(name)
        if e!=nil{
            t.Logf("M0_PLAN013_TLS_PLUS_LIVE_WINTUN_SAME_EPOCH_UNSUPPORTED native_Wintun_open=%v",e)
        }else{
            defer tun.Close()
            device:=CreatedWintun{TUN:tun}
            id,e:=device.Identity(ctx,[16]byte{17},cliSession.Epoch)
            if errors.Is(e,ErrNativeDeviceNotOwned){
                t.Logf("M0_PLAN013_TLS_PLUS_LIVE_WINTUN_SAME_EPOCH_UNSUPPORTED preexisting_or_foreign=%v",e)
            }else{
                if e!=nil{t.Fatal(e)}
                scoped,boundErr:=ConnectScopedOriginalTLSWintun(
                    ctx,native,tun,[16]byte{17},cliSession.Epoch)
                if boundErr!=nil{
                    if scoped!=nil{_ = scoped.StopRustScoped(ctx)}
                    t.Fatalf("typed original Go TLS->real M4 Wintun->Rust v2 owner refused: %v",boundErr)
                }
                // Same original Go credential TLS created an independently
                // authenticated Rust SERVER owner; hold the very same
                // real signed Wintun generation across BOTH M3 peers.
                if e:=resp.owner.BindOriginalM4NativeDevice(ctx,device,id);e!=nil{
                    t.Fatalf("original TLS peer Rust server native Wintun OS Hold failed: %v",e)
                }
                state,e:=native.OriginalOwnerReadback()
                if e!=nil||!state.DeviceBound||state.DeviceQuiesced||
                    !state.OwnerActive||state.ProductApplied{
                    t.Fatalf("actual TLS native driver binding false status: %+v err=%v",state,e)
                }
                installed=true
                // This is a REAL original-Go TLS + live M4 native Wintun
                // with Rust generation/hold, not a fabricated device.
                // The M4 owner intentionally refuses global WFP Apply:
                // confirm no WAL or OS mutation and no false GUI Connected.
                statePath:=filepath.Join(t.TempDir(),"native-original-state.json")
                admission,guardErr:=scoped.NativeProductAdmission(ctx,statePath)
                if !errors.Is(guardErr,windowsclient.ErrN4NativeGuard)||
                    admission.ProductApplied||!admission.OriginalTLSOwner.DeviceBound||
                    admission.OriginalTLSOwner.Generation==0||
                    admission.NativeIdentity.LUID!=id.LUID||
                    admission.DiskState.State!="absent" {
                    t.Fatalf("real signed Wintun+TLS bypassed M4 native WFP guard: %+v guard=%v",admission,guardErr)
                }
                for _,name:=range []string{statePath,statePath+".n4-owned-wal",statePath+".n4-owned-wal.routes"}{
                    if _,err:=os.Lstat(name);!errors.Is(err,os.ErrNotExist){
                        t.Fatalf("guard denial must never mutate native network WAL %s: %v",name,err)
                    }
                }

                // A real original-Go credential TLS client holds this
                // same signed Wintun generation while the actual Rust M1
                // original owner creates an M3 authenticated/immutable record.
                // The returned record is a carrier payload only. This test
                // does NOT claim real Windows UDP I/O for that ciphertext.
                ip:=make([]byte,40)
                ip[0]=0x45
                binary.BigEndian.PutUint16(ip[2:4],uint16(len(ip)))
                ip[8]=64;ip[9]=17
                copy(ip[12:16],[]byte{198,18,20,88})
                copy(ip[16:20],[]byte{198,18,20,77})
                binary.BigEndian.PutUint16(ip[20:22],41131)
                binary.BigEndian.PutUint16(ip[22:24],41132)
                binary.BigEndian.PutUint16(ip[24:26],20)
                ip[28]=0xa7
                // Real M3 Normal/off authenticated record seal, not a Go
                // crypto surrogate and not a second Rust owner.
                wire,seq,pn,e:=native.SealBoundOriginalNormalOff(ctx,ip)
                if e!=nil||len(wire)!=len(ip)+31||seq==0||
                    string(wire)==string(ip){
                    t.Fatalf("actual original TLS bound M1/M3 native packet seal refused: %v len=%d",e,len(wire))
                }
                // The same REAL Rust record now crosses an actual
                // signed Win32 WintunSendPacket, Windows IPv4 UDP kernel,
                // and a live socket bound to this adapter's /32.
                received:=m0RealOriginalTLSRustAEADToSignedWintunKernelApp(t,ctx,tun,wire)
                clear,e:=resp.owner.OpenBoundOriginalNormalOff(ctx,seq,received)
                if e!=nil||string(clear)!=string(ip){
                    t.Fatalf("ORIGINAL GO TLS peer Rust SERVER M3 failed to authenticate exact signed Wintun kernel UDP app ciphertext: %v",e)
                }
                if repeated,openErr:=resp.owner.OpenBoundOriginalNormalOff(ctx,seq,received);
                    openErr==nil||len(repeated)>0{
                    t.Fatal("real Wintun kernel delivered M3 packet replay accepted by original TLS Rust server")
                }
                tamperedServer:=append([]byte(nil),received...)
                tamperedServer[len(tamperedServer)-1]^=1
                if modified,openErr:=resp.owner.OpenBoundOriginalNormalOff(
                    ctx,seq+uint32(len(received)),tamperedServer);
                    openErr==nil||len(modified)>0{
                    t.Fatal("original TLS Rust server opened modified packet after signed Wintun kernel")
                }
                t.Logf("M0_PLAN020_REAL_ORIGINAL_GO_TLS_RUST_M3_PEER_DECRYPT_AFTER_SIGNED_WINTUN_KERNEL_UDP_APP_FIRST_DELIVERY_PASS seq=%d pn=%d replay_denied=1 tamper_denied=1",seq,pn)

                // The separately credential-authenticated SERVER Rust
                // sender now uses the same signed Wintun kernel in reverse.
                // The same CLIENT owner must authenticate its output.
                reverseIP:=append([]byte(nil),ip...)
                reverseIP[28]^=0x5a
                reverseWire,reverseSeq,reversePN,revErr:=resp.owner.SealBoundOriginalNormalOff(ctx,reverseIP)
                if revErr!=nil||len(reverseWire)!=len(reverseIP)+31{
                    t.Fatalf("real TLS Rust server reverse immutable M3 seal failed: %v",revErr)
                }
                reverseReceived:=m0RealOriginalTLSRustAEADToSignedWintunKernelApp(t,ctx,tun,reverseWire)
                reverseClear,revErr:=native.OpenBoundOriginalNormalOff(ctx,reverseSeq,reverseReceived)
                if revErr!=nil||string(reverseClear)!=string(reverseIP){
                    t.Fatalf("ORIGINAL TLS CLIENT Rust M3 failed to open same signed Wintun kernel reverse ciphertext: %v",revErr)
                }
                if again,openErr:=native.OpenBoundOriginalNormalOff(ctx,reverseSeq,reverseReceived);
                    openErr==nil||len(again)>0{
                    t.Fatal("same signed Wintun reverse M3 replay accepted")
                }
                t.Logf("M0_PLAN020_REAL_ORIGINAL_GO_TLS_DUAL_RUST_M3_AEAD_SIGNED_WINTUN_KERNEL_UDP_APP_BOTH_DIRECTIONS_PASS client_pn=%d server_pn=%d replay_denied=1 host_global_WFP_NOT_RUN=1",pn,reversePN)
                // Real original-Go credential TLS owner with a REAL
                // signed native Wintun Hold, not an invented token:
                // invalid peer AEAD and malformed records must never
                // return a packet for injection into a kernel ring.
                if decoded,openErr:=native.OpenBoundOriginalNormalOff(
                    ctx,seq,wire);openErr==nil||len(decoded)!=0{
                    t.Fatalf("real Rust owner self-TX ciphertext was incorrectly accepted as authenticated peer RX")
                }
                tampered:=append([]byte(nil),wire...)
                tampered[len(tampered)-1]^=1
                if decoded,openErr:=native.OpenBoundOriginalNormalOff(
                    ctx,seq,tampered);openErr==nil||len(decoded)!=0{
                    t.Fatalf("real Rust M3 receiver accepted unauthenticated modified record")
                }
                if decoded,openErr:=native.OpenBoundOriginalNormalOff(
                    ctx,seq,[]byte{0x45});openErr==nil||len(decoded)!=0{
                    t.Fatalf("short untrusted kernel M3 record decoded")
                }
                t.Log("M0_PLAN020_REAL_TLS_BOUND_SIGNED_WINTUN_RUST_M3_RECV_ABI_NEGATIVES_PASS same_held_device=1 invalid_peer=denied tampered=denied short=denied")
                t.Log("M0_PLAN013_TRUE_TLS_WINTUN_RUST_OS_PRODUCT_GUARD_DENIED_NO_WAL_MUTATION_PASS")
                if e=scoped.StopRustScoped(ctx);e!=nil{t.Fatal("M4 original native Wintun real quiesce->Rust owner Stop",e)}
                if e=resp.owner.StopScopedOwner(ctx);e!=nil{
                    t.Fatalf("original Go TLS Rust server native Wintun Stop failed: %v",e)
                }
                if stale,openErr:=resp.owner.OpenBoundOriginalNormalOff(ctx,seq,received);
                    openErr==nil||len(stale)>0{
                    t.Fatal("stale peer Rust M3 server reopened after native Wintun Stop")
                }
                if decoded,openErr:=native.OpenBoundOriginalNormalOff(
                    ctx,seq,wire);openErr==nil||len(decoded)!=0{
                    t.Fatalf("stale original TLS Rust owner RX used after Wintun Stop")
                }
                t.Log("M0_PLAN020_REAL_TLS_RUST_M3_RECEIVE_AFTER_NATIVE_WINTUN_QUIESCE_DENIED")
                t.Logf("M0_PLAN013_TLS_PLUS_LIVE_WINTUN_SAME_EPOCH_SCOPED_PASS real_m4_luid=%d index=%d os_applied=0 no_wfp_or_kernel_app=1",id.LUID,id.InterfaceIndex)
            }
        }
    }else{
        t.Log("M0_PLAN013_TLS_PLUS_LIVE_WINTUN_SAME_EPOCH_UNSUPPORTED explicit_probe_disabled")
    }
    if e=native.StopScopedOwner(ctx);e!=nil{t.Fatal(e)}
    if e=native.StopScopedOwner(ctx);e!=nil{t.Fatal("repeat protected native scoped Stop",e)}
    if e:=store.ReleaseLane("protected-owner",
        []byte("0123456789abcdef"),1,resp.session.Epoch);e!=nil{t.Fatal(e)}
    if installed{
        t.Log("M0_PLAN013_REAL_ORIGINAL_GO_TLS_M4_WINTUN_RUST_PROTECTED_STOP_SCOPED_PASS same_epoch=1 owned_hold_drained=1 network_os_applied=0")
    }
}
