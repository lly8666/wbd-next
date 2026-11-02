//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import (
    "context"
    "errors"
    "fmt"
    "io"
    "syscall"
    "testing"
    "time"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

func TestOriginalColdTLSRetryOnlyAfterAuthenticatedDeadAndRealWake(t *testing.T){
    timeout:=fmt.Errorf("fake tcp cold handshake: %w",context.DeadlineExceeded)
    if !originalColdRetryAllowed("client",true,false,0,timeout,nil){
        t.Fatal("cold TLS timeout after authenticated dead must be bounded retryable")
    }
    for _,tc:=range []struct{
        name,role string
        auth,ready bool
        retries int
        runErr,closeErr error
    }{
        {"initial_without_dead","client",false,false,0,timeout,nil},
        {"server_not_active_cold_dialer","server",true,false,0,timeout,nil},
        {"already_ready","client",true,true,0,timeout,nil},
        {"quota_spent","client",true,false,2,timeout,nil},
        {"credential_rejected","client",true,false,0,errors.New("authentication refused"),nil},
        {"unexpected_eof","client",true,false,0,io.EOF,nil},
        {"owned_close_failed","client",true,false,0,timeout,errors.New("close failed")},
    }{
        t.Run(tc.name,func(t *testing.T){
            if originalColdRetryAllowed(tc.role,tc.auth,tc.ready,tc.retries,tc.runErr,tc.closeErr){
                t.Fatal("cold TLS retry violates authenticated-dead/Stop/credentials boundary")
            }
        })
    }
    if !nativeColdTLSRetryable(faketcp.ErrBootstrapTimeout){
        t.Fatal("original retry exhaustion is transient cold transport, not an auth rejection")
    }
    if nativeColdFailureClass(timeout)!="timeout"||
       nativeColdFailureClass(syscall.ETIMEDOUT)!="timeout"||
       nativeColdFailureClass(errors.New("bad certificate"))!="other"{
        t.Fatal("safe fixed-category reporting must not leak or mask TLS auth failures")
    }
}

func TestOriginalColdFakeTCPActuallyRetriesSYNWhenServerNotReady(t *testing.T){
    // This is a transport-retry unit test, not a product cold budget.
    // Explicitly install the local SYN ceiling that real Rust would supply
    // before NewClientAssociation; never resurrect a production 1360 fallback.
    if err:=faketcp.SetPublicV4AdvertisedMSS(1420);err!=nil{t.Fatal(err)}

    flow:=faketcp.ClientFlow{LocalIP:[4]byte{10,22,1,2},
        PeerIP:[4]byte{10,22,1,1},LocalPort:41031,PeerPort:443}
    count:=0
    assoc,e:=faketcp.NewClientAssociation(flow,1234,time.Second,
        func(faketcp.Segment)error{count++;return nil})
    if e!=nil{t.Fatal(e)}
    defer assoc.Close()
    if e=assoc.Start(time.Now());e!=nil{t.Fatal(e)}
    ctx,stop:=context.WithTimeout(context.Background(),2300*time.Millisecond)
    defer stop()
    e=waitForOriginalColdSYN(ctx,assoc)
    if !errors.Is(e,context.DeadlineExceeded){
        t.Fatalf("no real server, association must time out: %v",e)
    }
    if count<2||count>4{
        t.Fatalf("original FakeTCP SYN RTO did not fire: %d",count)
    }
}
