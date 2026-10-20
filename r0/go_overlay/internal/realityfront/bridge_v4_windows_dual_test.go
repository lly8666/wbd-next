//go:build windows && wbd_v4_embedded_go
package realityfront

import (
    "context"
    "crypto/tls"
    "errors"
    "fmt"
    "os"
    "testing"

    "github.com/lly8666/wobuzhidao/internal/windowsclient"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// Two ACTUAL original Go FakeTCP associations, not a net.Pipe pretending
// to supply a ClientAssociation Detach receipt. They exchange normal
// SYN/SYNACK/ACK/TLS protected data segments in a bounded in-process wire.
// Windows WFP and OS packet delivery are separately NOT_RUN.
func TestM0WindowsTwoOriginalGoFakeTCPProtectedTLSRustOwnersAllCiphers(t *testing.T) {
    lib:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
    if lib==""{t.Fatal("same-source Windows native Rust DLL must be present")}
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            srvOwner,e:=newV4WindowsPrivateOwnerBridge(lib)
            if e!=nil{t.Fatal(e)}
            cliOwner,e:=newV4WindowsPrivateOwnerBridge(lib)
            if e!=nil{t.Fatal(e)}
            // Conservative original Go production gate: ONLY Normal/off
            // may be represented, never a feature7 or Game authorization.
            policy:=v4TestPolicy(1,cipher)
            policy.FECMode=FECOff
            policy.FixedParity=0
            flow:=faketcp.ClientFlow{
                LocalIP:[4]byte{10,77,0,2},PeerIP:[4]byte{10,77,0,1},
                LocalPort:41401,PeerPort:443,
            }
            toServer:=make(chan faketcp.Segment,4096)
            toClient:=make(chan faketcp.Segment,4096)
            copyAndEmit:=func(out chan<- faketcp.Segment)faketcp.SegmentEmitter{
                return func(seg faketcp.Segment)error{
                    seg.Payload=append([]byte(nil),seg.Payload...)
                    select {case out<-seg:return nil
                    default:return errors.New("bounded original Go packet channel full")}
                }
            }
            client,e:=faketcp.NewClientAssociation(flow,123456,time.Second,copyAndEmit(toServer))
            if e!=nil{t.Fatal(e)}
            defer client.Close()
            if e=client.Start(time.Now());e!=nil{t.Fatal(e)}
            syn:=<-toServer
            server,e:=faketcp.NewServerAssociation(syn,31337,time.Second,copyAndEmit(toClient))
            if e!=nil{t.Fatal(e)}
            defer server.Close()
            synack,e:=server.SYNACKSegment()
            if e!=nil{t.Fatal(e)}
            if e=client.HandleSegment(synack,time.Now());e!=nil{t.Fatal(e)}
            ack:=<-toServer
            if _,e=server.HandleSegment(ack,time.Now());e!=nil{t.Fatal(e)}
            done:=make(chan struct{})
            defer close(done)
            routerError:=make(chan error,1)
            sendErr:=func(err error){
                if err!=nil{select {case routerError<-err:default:}}
            }
            go func(){
                for{
                    select{
                    case <-done:return
                    case seg:=<-toServer:
                        result,err:=server.HandleSegment(seg,time.Now())
                        if err!=nil{sendErr(err);return}
                        if result.AckNeeded{
                            sendErr(copyAndEmit(toClient)(server.ACKSegment(result.Ack)))
                        }
                    case seg:=<-toClient:
                        if err:=client.HandleSegment(seg,time.Now());err!=nil{
                            sendErr(err);return
                        }
                    }
                }
            }()
            store,e:=NewV4EpochStore(1)
            if e!=nil{t.Fatal(e)}
            cert:=makeServerCert(t)
            routeKey:=[]byte("0123456789abcdef0123456789abcdef")
            type result struct{s *V4ServerSession;e error}
            resultCh:=make(chan result,1)
            go func(){
                session,err:=EstablishServerV4(context.Background(),server,ServerAdmissionConfig{
                    TLS:ServerConfig{ServerName:"target.test",RouteKey:routeKey,
                        TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},
                        Timeout:4*time.Second},
                    ExpectedUsername:"protected-owner",ExpectedPassword:"secret",
                    ServerLimit:1400,
                },V4ServerOptions{DataPlaneReady:true,Epochs:store,ownerBridge:srvOwner})
                resultCh<-result{session,err}
            }()
            ctx,cancel:=context.WithTimeout(context.Background(),5*time.Second)
            defer cancel()
            cliSession,clientErr:=cliOwner.connectVerifiedClient(ctx,client,ClientAdmissionConfig{
                TLS:ClientConfig{ServerName:"target.test",RouteKey:routeKey,Timeout:4*time.Second},
                Username:"protected-owner",Password:"secret",TunnelID:[]byte("0123456789abcdef"),
                ClientLimit:1400,LaneID:1,DesiredLanes:1,Policy:policy,
            })
            var answer result
            select{
            case answer= <-resultCh:
            case <-time.After(6*time.Second):
                t.Fatal("same-source dual original FakeTCP/TLS protected server timed out")
            }
            if clientErr!=nil||answer.e!=nil||cliSession==nil||answer.s==nil{
                var packetErr error
                select{case packetErr=<-routerError:default:}
                t.Fatalf("original protected dual handoff failed client=%v server=%v packet=%v",
                    clientErr,answer.e,packetErr)
            }
            cc,ce:=cliSession.ColdSnapshot()
            sc,se:=answer.s.ColdSnapshot()
            if ce!=nil||se!=nil||cc.Epoch()!=sc.Epoch() ||
                cc.ServerSide()||!sc.ServerSide()||
                cliOwner.handle==0||srvOwner.handle==0||
                cliOwner.handle==srvOwner.handle{
                t.Fatalf("original exporter identity/generation mismatch client=%v server=%v",ce,se)
            }
            for _,owner:=range []*v4WindowsNativeOwnerBridge{cliOwner,srvOwner}{
                st,err:=owner.state()
                if err!=nil||st.phase!=2||st.applied!=0||st.loansDrained!=0 ||
                    st.server!=map[bool]uint32{true:1,false:0}[owner.serverSide] {
                    t.Fatalf("original TLS role native Rust no-fake-applied: %+v err=%v",st,err)
                }
            }
            // Exact authenticated Rust generation is NOT sufficient to
            // borrow an arbitrary native Wintun: prove the OS device is
            // process-created, LIVE and GUID+LUID+index bound before the
            // Rust device lifetime fence. Empty/borrowed devices fail.
            for _,owner:=range []*v4WindowsNativeOwnerBridge{cliOwner,srvOwner}{
                st,err:=owner.realNativeDeviceState()
                if err!=nil||st.Version!=2||st.Bound!=0||st.Applied!=0{
                    t.Fatalf("credential TLS attached phantom Windows device: %+v err=%v",st,err)
                }
                fake:=&windowsclient.TUN{}
                supplied:=windowsclient.N4UnifiedIdentity{
                    Installation:[16]byte{17},Generation:owner.epoch,
                    WintunLUID:7,WintunIndex:7,WintunGUID:"11111111-2222-3333-4444-555555555555",
                    AdapterAlias:"WBD-foreign",
                }
                if lease,e:=owner.holdOriginalCreatedWintun(context.Background(),fake,supplied);
                    !errors.Is(e,errV4WindowsOwner)||lease!=nil{
                    t.Fatalf("unowned Wintun or foreign alias joined real TLS Rust: lease=%v err=%v",lease,e)
                }
                // A mutated epoch MUST fail before invoking M4/native OS.
                supplied.Generation=[16]byte{55}
                if lease,e:=owner.holdOriginalCreatedWintun(context.Background(),fake,supplied);
                    !errors.Is(e,errV4WindowsOwner)||lease!=nil{
                    t.Fatalf("stale epoch obtained Win native lease: lease=%v err=%v",lease,e)
                }
            }
            if cipher==CipherChaCha && os.Getenv("WBD_M0_TRY_SCOPED_NATIVE_WINTUN")=="1"{
                name:=fmt.Sprintf("WBD-M0-PLAN013-%s",os.Getenv("GITHUB_RUN_ID"))
                tun,openErr:=windowsclient.OpenTUN(name)
                if openErr!=nil{
                    // CI's legally unprivileged runner may not contain the
                    // real Wintun DLL/driver. This is UNSUPPORTED, not PASS.
                    t.Logf("M0_PLAN013_REAL_CREATED_WINTUN_OS_LEASE_UNSUPPORTED open=%v",openErr)
                }else{
                    defer tun.Close()
                    actual,actualErr:=tun.NativeIdentity(context.Background())
                    if actualErr!=nil{
                        t.Fatalf("real process-created Wintun native identity failure: %v",actualErr)
                    }
                    if !actual.CreatedByProcess{
                        t.Log("M0_PLAN013_REAL_CREATED_WINTUN_OS_LEASE_UNSUPPORTED borrowed_existing")
                    }else{
                        id,e:=v4WindowsOriginalWintunIdentity(context.Background(),
                            tun,[16]byte{17},cliOwner.epoch)
                        if e!=nil{t.Fatalf("same-process actual GUID LUID identity: %v",e)}
                        lease,e:=cliOwner.holdOriginalCreatedWintun(context.Background(),tun,id)
                        if e!=nil{t.Fatalf("exact original Go TLS to M4 live Wintun Hold: %v",e)}
                        if err:=cliOwner.stopRustOwnerOnly();!errors.Is(err,errV4WindowsOwner){
                            t.Fatalf("live original M4 Wintun did not block unquiesced Rust Stop: %v",err)
                        }
                        if e:=lease.quiesceAndStopRustOnly(context.Background());e!=nil{
                            t.Fatalf("exact real Wintun lease→Rust quiesce→Stop: %v",e)
                        }
                        t.Logf("M0_PLAN013_REAL_CREATED_WINTUN_RUST_OWNER_LIFETIME_STOP_PASS os_luid=%d ifindex=%d product_applied=0 no_kernel_udp_claim=1",
                            id.WintunLUID,id.WintunIndex)
                    }
                }
            }
            // Actual Rust owner Stop first, before original-Go epoch/pipe
            // cleanup, and both terminal tokens cannot revive after release.
            for _,owner:=range []*v4WindowsNativeOwnerBridge{cliOwner,srvOwner}{
                if err:=owner.stopRustOwnerOnly();err!=nil{t.Fatal(err)}
                if err:=owner.stopRustOwnerOnly();err!=nil{t.Fatal(err)}
                if _,err:=owner.state();!errors.Is(err,errV4WindowsOwner){
                    t.Fatalf("stale owner state still live: %v",err)
                }
            }
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),
                1,answer.s.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}

func TestM0WindowsActualClientOwnerRejectsUnsupportedBeforeNetworkOrRust(t *testing.T){
    lib:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
    if lib==""{t.Fatal("no native Windows DLL")}
    b,err:=newV4WindowsPrivateOwnerBridge(lib)
    if err!=nil{t.Fatal(err)}
    // Neither a nil original transport nor forged operator Game/FEC flags
    // can activate a Rust owner or emit a protected TLS packet.
    cfg:=ClientAdmissionConfig{DesiredLanes:1,Policy:v4TestPolicy(1,CipherChaCha)}
    _,err=b.connectVerifiedClient(context.Background(),nil,cfg)
    if !errors.Is(err,errV4WindowsOwner){t.Fatalf("nil association accepted: %v",err)}
    if b.handle!=0||b.committed||b.stopped{t.Fatal("unauthorized token")}
}
