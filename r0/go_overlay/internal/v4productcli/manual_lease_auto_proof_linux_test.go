//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "testing"

    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// The existing manual-only negative test must remain valid; named-auto is
// not a bypass for a caller-invented tunnel or a cross-account identity.
func TestPLAN028NamedRosterAutoIPRequiresDerivedAuthenticatedTunnel(t *testing.T) {
    c:=config{manualClientLeases4:map[string]string{
        "alice":"10.66.0.2/32","bob":"10.66.0.3/32",
    }}
    var install logicaltunnel.InstallationID
    install[0]=0x4b
    install[15]=0x16
    derived:=logicaltunnel.DerivedTunnelID("bob",install)
    good:=realityfront.AdmissionRequest{
        Username:"bob",AutoLease:true,
        TunnelID:append([]byte(nil),derived[:]...),
        InstallationID:append([]byte(nil),install[:]...),
    }
    if err:=originalV4ManualAccountTunnelAfterAuth(c,good);err!=nil{
        t.Fatalf("real username+installation-derived automatic tunnel rejected: %v",err)
    }
    bogusID:=good
    bogusID.TunnelID=make([]byte,16)
    bogusID.TunnelID[0]=1
    if err:=originalV4ManualAccountTunnelAfterAuth(c,bogusID);err==nil{
        t.Fatal("arbitrary manual tunnel with automatic lease accepted")
    }
    missingInstallation:=good
    missingInstallation.InstallationID=nil
    if err:=originalV4ManualAccountTunnelAfterAuth(c,missingInstallation);err==nil{
        t.Fatal("auto lease accepted without installation")
    }
    zeroInstallation:=good
    zeroInstallation.InstallationID=make([]byte,16)
    if err:=originalV4ManualAccountTunnelAfterAuth(c,zeroInstallation);err==nil{
        t.Fatal("auto lease accepted zero installation")
    }
    crossAccount:=good
    crossAccount.Username="alice"
    if err:=originalV4ManualAccountTunnelAfterAuth(c,crossAccount);err==nil{
        t.Fatal("identity derived for bob accepted as alice")
    }
    unknown:=good
    unknown.Username="mallory"
    if err:=originalV4ManualAccountTunnelAfterAuth(c,unknown);err==nil{
        t.Fatal("unknown credential selected a named lease")
    }
    c.manualClientLeases4=nil
    c.tunnel[0]=1
    if err:=originalV4ManualAccountTunnelAfterAuth(c,good);err==nil{
        t.Fatal("legacy singleton permitted automatic named lease")
    }
}
