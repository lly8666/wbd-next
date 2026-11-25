package main

import (
    "log"
    "os"
    "os/signal"
    "syscall"
)

// Only cold harness entry; actual TPROXY/splice Go wrapper and Rust source
// are copied verbatim (except Go package declaration) at build time.
type config struct {
    tunName string
    tcpProxyPort int
    tcpProxyCC string
}
func main() {
    p,e:=startOwnedTCPSplice(config{tunName:"h19in",tcpProxyPort:46180,tcpProxyCC:"cubic"})
    if e!=nil{log.Fatal(e)}
    sig:=make(chan os.Signal,1)
    signal.Notify(sig,syscall.SIGTERM,syscall.SIGINT)
    <-sig
    if e=p.Close();e!=nil{log.Fatal(e)}
}
