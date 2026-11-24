//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import (
 "fmt"
 "strings"
 "testing"
 "strconv"
)

// Host runs production classifier only. No simulated NIC, fake server,
// Android emulation, protected admission or TLS success.
func TestAndroidA31OriginalGoColdParseFixedReasons(t *testing.T){
 cases:=[]struct{reason string;cause error}{
  {"FLAG_SYNTAX",fmt.Errorf("flag provided but not defined: -not-a-real-option")},
  {"PASSWORD_FILE",fmt.Errorf("invalid password-file: open /data/secret: permission denied")},
  {"ROUTE_KEY_FILE",fmt.Errorf("invalid route-key-hex-file: secret must be a regular owner-only file")},
  {"ROUTE_KEY_VALUE",fmt.Errorf("route-key (8..32 alphanumeric) or legacy 32-byte route-key-hex required; no online bootstrap")},
  {"INSTALLATION_ID",fmt.Errorf("installation-id-file: open private file: permission denied")},
  {"CN_GEOSITE_FILE",fmt.Errorf("signed Android CN8503 cold source rejected: invalid pinned source")},
  {"TLS_CA_FILE",fmt.Errorf("load server TLS trust PEM: open private pem: permission denied")},
  {"ALL_APP_EXCLUSIONS",fmt.Errorf("excluded app IDs must be unique sorted 10000..19999")},
  {"ANDROID_NETWORK_SCOPE",fmt.Errorf("Android root client needs explicit physical Network handle")},
  {"PEER_ADDRESS",fmt.Errorf("peer-host requires a valid Android physical bootstrap DNS name")},
  {"REQUIRED_COLD_SETTINGS",fmt.Errorf("missing/invalid real original V4 TLS/raw/TUN settings")},
  {"POLICY",fmt.Errorf("tun-txqlen-packets must be 500 or 2048")},
  {"OTHER",fmt.Errorf("confidential internal failure /data/secret username=private")},
 }
 for _,tc:=range cases{
  got:=originalAndroidColdParseClass(tc.cause)
  if got!=tc.reason{t.Fatalf("reason %s got %s",tc.reason,got)}
  if strings.Contains(got,"secret")||strings.Contains(got,"/data/")||
     strings.Contains(got,"username")||strings.Contains(got,"private")||
     strings.Contains(got," ")||strings.Contains(got,"="){
   t.Fatalf("diagnostic class contains untrusted data: %q",got)
  }
 }
 if got:=originalAndroidColdParseClass(nil);got!="OTHER"{
  t.Fatalf("nil rejected as %s",got)
 }
}

func TestAndroidA37OriginalGoCertMainDefaultAndStrictOptIn(t *testing.T){
 args:=[]string{
  "--raw-interface","eth0","--local-ip","192.0.2.10","--local-port","43900",
  "--peer-ip","198.51.100.7","--peer-port","443","--tun-name","wbdv40",
  "--tun-ipv4","10.66.0.8/32","--server-name","wbd.example.test",
  "--mode","normal","--username","user","--password","secret",
  "--route-key-hex",strings.Repeat("a",64),
  "--tunnel-id","0123456789abcdef0123456789abcdef",
 }
 plain,e:=parse("client",args)
 if e!=nil{t.Fatalf("original-Go main default parse: %v",e)}
 if plain.tlsVerifyServer{t.Fatal("default must be main compatible: off")}
 strict,e:=parse("client",append(append([]string{},args...),"--tls-verify-server"))
 if e!=nil{t.Fatalf("original-Go strict parse: %v",e)}
 if !strict.tlsVerifyServer{t.Fatal("strict opt-in ignored")}
}

func TestB58OriginalGoColdSixteenSelectedUIDs(t *testing.T){
 ids:=make([]string,16)
 for i:=range ids{ids[i]=strconv.Itoa(11000+i)}
 got,err:=parseAndroidRouteGroupArg(strings.Join(ids,","))
 if err!=nil||len(got)!=16||got[0]!=11000||got[15]!=11015{
  t.Fatalf("16 Go app UIDs lost in native cold parser: %v %v",got,err)
 }
 if _,err=parseAndroidRouteGroupArg(strings.Join(ids,",")+",11016");err==nil{
  t.Fatal("17 selected App UIDs must not be truncated")
 }
}
