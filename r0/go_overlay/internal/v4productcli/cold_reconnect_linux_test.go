//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import (
    "context"
    "errors"
    "fmt"
    "io"
    "syscall"
    "testing"
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
    if nativeColdFailureClass(timeout)!="timeout"||
       nativeColdFailureClass(syscall.ETIMEDOUT)!="timeout"||
       nativeColdFailureClass(errors.New("bad certificate"))!="other"{
        t.Fatal("safe fixed-category reporting must not leak or mask TLS auth failures")
    }
}
