//go:build windows
package main

import (
 "errors"
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
 Username,Password string
 TunnelID [16]byte
 Installation [16]byte
 Lease4 netip.Prefix
 AdapterAlias,StatePath string
 DNSServers4 []netip.Addr
 Direct4,Bypass4 []netip.Prefix
 TunnelMTU uint32
 ControlStdin bool
 Mode m0WindowsV4Mode
 FEC2Mode,FEC2Profile,FEC2AutoPolicy,FEC2AutoStartProfile string
 // Explicit cold original Rust Health policy. Zero means 15/90/0 defaults;
 // the real M2 TX clock returns the effective, not GUI intent.
 HealthIntervalSeconds,HealthDeadSeconds,HealthDormantSeconds uint32
}
var errM0NativeV4PacketBridge=errors.New("Windows original Go native V4 TLS authenticated, but public Rust M3 TCP/Wintun application packet bridge and full OS Applied/Stop remain NOT_RUN; refusing production network activation")
