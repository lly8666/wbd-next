//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
    "context"
    "errors"
    "path/filepath"
    "strings"
    "testing"

    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// This exercises the actual mixed-mode entry guard with manual /32 accounts.
// Deliberately stop at a missing TLS certificate: no network, forged TLS,
// Rust native worker or false READY is involved in this cold-path unit.
func TestPLAN028MixedManualAccountReachesTLSCertificateStage(t *testing.T) {
    c:=config{
        role:"server",mixedModes:true,
        manualClientLeases4:map[string]string{
            "alice":"10.66.0.2/32","bob":"10.66.0.3/32",
        },
        tlsCert:filepath.Join(t.TempDir(),"h1510-missing-cert.pem"),
        tlsKey:"h1510-missing-key.pem",
    }
    err:=runGame(context.Background(),c,0,nil,nil,nil,nil)
    if err==nil||errors.Is(err,realityfront.ErrAdmissionUnsupported)||
       !strings.Contains(err.Error(),"h1510-missing-cert.pem"){
        t.Fatalf("manual mixed server should reach genuine cold TLS cert loading: %v",err)
    }
    c.manualClientLeases4=nil
    err=runGame(context.Background(),c,0,nil,nil,nil,nil)
    if !errors.Is(err,realityfront.ErrAdmissionUnsupported){
        t.Fatalf("shared server without protected address authority must reject: %v",err)
    }
}
