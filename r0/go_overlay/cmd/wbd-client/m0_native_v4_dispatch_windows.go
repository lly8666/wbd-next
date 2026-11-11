//go:build windows
package main

import (
 "errors"
 "crypto/x509"
 "fmt"
 "os"
 "net/netip"
)
// Mainline Windows CLI needs real V4 ownership, not a V3/PowerShell
// fallback. Without the source-locked native V4 build tag this is
// deliberately unavailable and cannot emit an OS Applied status.
type m0NativeV4Options struct {
 ServerIP netip.Addr
 ServerPort,SourcePort uint16
 ServerName string
 RouteKey []byte
 TrustedServerRoots *x509.CertPool
 Username,Password string
 TunnelID [16]byte
 Installation [16]byte
 Lease4 netip.Prefix
 // For AutoLease, Lease4 is 0.0.0.0/32 until the protected TLS reply.
 AutoLease bool
 RecordCipher uint8 // exact per-client protected V4 AEAD, never a server-global switch
 AdapterAlias,StatePath string
 DNSServers4 []netip.Addr
 Direct4,Bypass4 []netip.Prefix
 TunnelMTU uint32 // derived inner Wintun IPv4 MTU
 ConnectionMTU uint32 // exact original --mtu outer NPF IPv4/TCP MTU
 ControlStdin bool
 DisableOuterRepair bool
 Mode m0WindowsV4Mode
 FEC2Mode,FEC2Profile,FEC2AutoPolicy,FEC2AutoStartProfile string
 // Explicit cold original Rust Health policy. Zero means 15/90/0 defaults;
 // the real M2 TX clock returns the effective, not GUI intent.
 HealthIntervalSeconds,HealthDeadSeconds,HealthDormantSeconds uint32
}
var errM0NativeV4PacketBridge=errors.New("Windows original Go native V4 TLS authenticated, but public Rust M3 TCP/Wintun application packet bridge and full OS Applied/Stop remain NOT_RUN; refusing production network activation")

// Application-scoped TLS trust: a locally imported server certificate/CA
// adds no system-wide trust and never skips hostname/signature validation.
func m0LoadWindowsV4ServerRoots(path string)(*x509.CertPool,error){
 if path==""{return nil,nil} // Use ordinary Windows system roots.
 raw,err:=os.ReadFile(path)
 if err!=nil{return nil,fmt.Errorf("trusted server PEM: %w",err)}
 if len(raw)==0||len(raw)>1<<20{return nil,fmt.Errorf("trusted server PEM invalid size")}
 roots:=x509.NewCertPool()
 if !roots.AppendCertsFromPEM(raw){return nil,fmt.Errorf("trusted server PEM contains no certificate")}
 return roots,nil
}
