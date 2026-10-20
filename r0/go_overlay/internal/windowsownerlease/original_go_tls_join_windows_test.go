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
    "errors"
    "fmt"
    "math/big"
    "os"
    "path/filepath"
    "testing"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
    "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
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
    ctx,cancel:=context.WithTimeout(context.Background(),12*time.Second)
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
    type response struct{session *realityfront.V4ServerSession;err error}
    answer:=make(chan response,1)
    go func(){
        session,err:=realityfront.EstablishServerV4(ctx,server,
            realityfront.ServerAdmissionConfig{
                TLS:realityfront.ServerConfig{
                    ServerName:"target.test",RouteKey:routeKey,
                    TLSConfig:&tls.Config{Certificates:[]tls.Certificate{m0WinJoinCert(t)}},
                    Timeout:5*time.Second,
                },
                ExpectedUsername:"protected-owner",ExpectedPassword:"secret",
                ServerLimit:1400,
            },realityfront.V4ServerOptions{DataPlaneReady:true,Epochs:store})
        answer<-response{session,err}
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
    if err!=nil||resp.err!=nil||native==nil||cliSession==nil||resp.session==nil{
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
                t.Log("M0_PLAN013_TRUE_TLS_WINTUN_RUST_OS_PRODUCT_GUARD_DENIED_NO_WAL_MUTATION_PASS")
                if e=scoped.StopRustScoped(ctx);e!=nil{t.Fatal("M4 original native Wintun real quiesce->Rust owner Stop",e)}
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
