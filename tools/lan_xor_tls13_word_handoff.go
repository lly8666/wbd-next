// Standalone insecure LAN XOR fixture. A REAL mutually authenticated TLS 1.3
// handshake takes place first; then both peers deliberately bypass TLS and
// send fake TLS-like 0x17 records. This is NOT an RFC-compliant TLS data stream,
// NOT the WBD Go bootstrap and NOT a production transport implementation.
package main

import (
    "bytes"
    "crypto/ed25519"
    "crypto/rand"
    "crypto/tls"
    "crypto/x509"
    "crypto/x509/pkix"
    "encoding/binary"
    "errors"
    "fmt"
    "io"
    "math/big"
    "math/bits"
    "net"
    "os"
    "strconv"
    "time"
)

const seed uint64 = 0x74babe329afe5b13 // publicly known fixture; NOT a cryptographic key
const recordBodyMax = (1 << 14) + 256

func ipv4Packet() []byte {
    const n = 1345
    p := make([]byte, n)
    p[0] = 0x45
    binary.BigEndian.PutUint16(p[2:4], uint16(n))
    p[6] = 0x40; p[8] = 64; p[9] = 6
    copy(p[12:20], []byte{10,11,12,13,10,21,22,23})
    copy(p[20:24], []byte{0x12,0x34,0x01,0xbb})
    binary.BigEndian.PutUint32(p[24:28], 140851678)
    p[32] = 0x50
    for i := 40; i < n; i++ { p[i] = byte(((i-40)*37+11)&255) }
    return p
}
func mix64(x uint64) uint64 {
    x += 0x9e3779b97f4a7c15
    x = (x ^ (x>>30)) * 0xbf58476d1ce4e5b9
    x = (x ^ (x>>27)) * 0x94d049bb133111eb
    return x ^ (x >> 31)
}
func mask(b []byte, rolling bool, pn uint64) {
    if !rolling {
        for i := range b { b[i] ^= 0xa5 }
        return
    }
    state := mix64(seed ^ bits.RotateLeft64(pn, 17) ^ 0x4c414e5f584f525f)
    for i := 0; i < len(b); i += 8 {
        state ^= state >> 12
        state ^= state << 25
        state ^= state >> 27
        ks := state * 0x2545f4914f6cdd1d
        for j := 0; j < 8 && i+j < len(b); j++ { b[i+j] ^= byte(ks >> (8*j)) }
    }
}
// Optimized word-wise application of the IDENTICAL legacy rolling keystream.
// This is strictly noncryptographic and never supplies integrity protection.
func maskWord(b []byte, pn uint64) {
    state := mix64(seed ^ bits.RotateLeft64(pn, 17) ^ 0x4c414e5f584f525f)
    i:=0
    for ;i+8<=len(b);i+=8 {
        state ^= state >> 12
        state ^= state << 25
        state ^= state >> 27
        ks := state * 0x2545f4914f6cdd1d
        binary.LittleEndian.PutUint64(b[i:i+8],binary.LittleEndian.Uint64(b[i:i+8])^ks)
    }
    if i<len(b) {
        state ^= state >> 12
        state ^= state << 25
        state ^= state >> 27
        ks := state * 0x2545f4914f6cdd1d
        for j:=0;i+j<len(b);j++ {b[i+j]^=byte(ks>>(8*j))}
    }
}
func verifyWordEquivalence() error {
    for _,n:=range []int{0,1,2,3,4,5,6,7,8,9,15,16,17,63,64,65,127,128,129,1347,16397} {
        for _,pn:=range []uint64{0,1,2,3,9,255,256,65535,0xffffffff,^uint64(0)} {
            a:=make([]byte,n)
            for i:=range a { a[i]=byte((i*53+91)&255) }
            b:=append([]byte{},a...)
            mask(a,true,pn)
            maskWord(b,pn)
            if !bytes.Equal(a,b) {return fmt.Errorf("word mismatch length=%d pn=%d",n,pn)}
            maskWord(b,pn)
            for i:=range b { if b[i]!=byte((i*53+91)&255) {return errors.New("word involution failed")} }
        }
    }
    return nil
}

func seal(p []byte, rolling bool, fastWord bool, pn uint64) []byte {
    if len(p) < 20 || len(p)+10 > recordBodyMax { panic("packet too large") }
    b := make([]byte, len(p)+15)
    copy(b[:3], []byte{0x17,0x03,0x03})
    binary.BigEndian.PutUint16(b[3:5], uint16(10+len(p)))
    binary.BigEndian.PutUint64(b[5:13], pn)
    binary.BigEndian.PutUint16(b[13:15], uint16(len(p)))
    copy(b[15:], p)
    if fastWord {maskWord(b[13:],pn)} else {mask(b[13:], rolling, pn)}
    return b
}
func open(w []byte, rolling bool, fastWord bool) ([]byte, uint64, error) {
    if len(w) < 35 || !bytes.Equal(w[:3], []byte{0x17,0x03,0x03}) || int(binary.BigEndian.Uint16(w[3:5])) + 5 != len(w) {
        return nil, 0, errors.New("invalid TLS-like frame")
    }
    pn := binary.BigEndian.Uint64(w[5:13])
    b := append([]byte{}, w[13:]...)
    if fastWord {maskWord(b,pn)} else {mask(b,rolling,pn)}
    if int(binary.BigEndian.Uint16(b[:2])) != len(b)-2 || b[2]>>4 != 4 {
        return nil, 0, errors.New("invalid IPv4 fixture body")
    }
    return b[2:], pn, nil
}
func testCert() (tls.Certificate, *x509.CertPool, error) {
    pub, priv, err := ed25519.GenerateKey(rand.Reader)
    if err != nil { return tls.Certificate{}, nil, err }
    now := time.Now()
    tmpl := &x509.Certificate{
        SerialNumber:big.NewInt(1), Subject:pkix.Name{CommonName:"localhost"},
        NotBefore:now.Add(-time.Hour), NotAfter:now.Add(time.Hour),
        KeyUsage:x509.KeyUsageDigitalSignature|x509.KeyUsageCertSign,
        ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth,x509.ExtKeyUsageClientAuth},
        BasicConstraintsValid:true, IsCA:true, DNSNames:[]string{"localhost"},
    }
    der, err := x509.CreateCertificate(rand.Reader,tmpl,tmpl,pub,priv)
    if err != nil { return tls.Certificate{}, nil, err }
    parsed, err := x509.ParseCertificate(der)
    if err != nil { return tls.Certificate{}, nil, err }
    pool := x509.NewCertPool()
    pool.AddCert(parsed)
    return tls.Certificate{Certificate:[][]byte{der},PrivateKey:priv,Leaf:parsed},pool,nil
}
func errf(e error) { if e != nil { panic(e) } }

func run(port int) error {
    if err:=verifyWordEquivalence();err!=nil {return err}
    cert, pool, err := testCert()
    if err != nil { return err }
    listener, err := net.Listen("tcp", net.JoinHostPort("127.0.0.1", strconv.Itoa(port)))
    if err != nil { return err }
    defer listener.Close()
    address := listener.Addr().String()
    scfg := &tls.Config{
        MinVersion:tls.VersionTLS13, MaxVersion:tls.VersionTLS13,
        Certificates:[]tls.Certificate{cert}, ClientAuth:tls.RequireAndVerifyClientCert,
        ClientCAs:pool, SessionTicketsDisabled:true,
    }
    ccfg := &tls.Config{
        MinVersion:tls.VersionTLS13, MaxVersion:tls.VersionTLS13,
        ServerName:"localhost", RootCAs:pool, Certificates:[]tls.Certificate{cert},
        SessionTicketsDisabled:true,
    }
    expected := ipv4Packet()
    serverResult := make(chan error, 1)
    go func() {
        raw, e := listener.Accept()
        if e != nil {serverResult <- e; return}
        defer raw.Close()
        e = raw.SetDeadline(time.Now().Add(15*time.Second))
        if e != nil {serverResult <- e; return}
        conn := tls.Server(raw, scfg)
        if e = conn.Handshake(); e != nil {serverResult <- e; return}
        if conn.ConnectionState().Version != tls.VersionTLS13 {serverResult <- errors.New("server TLS version");return}
        // A real TLS-protected two-sided switch barrier. Handshake completion
        // alone is not a peer-ready signal: racing the raw handoff can corrupt
        // stream boundaries or close a peer on differently scheduled hosts.
        var ready [7]byte
        if _,e=io.ReadFull(conn,ready[:]);e!=nil {serverResult<-fmt.Errorf("server encrypted ready read: %w",e);return}
        if string(ready[:])!="C_READY" {serverResult<-errors.New("invalid client TLS-ready marker");return}
        if _,e=conn.Write([]byte("S_READY"));e!=nil {serverResult<-fmt.Errorf("server encrypted ready write: %w",e);return}
        direct := conn.NetConn()
        for i:=0; i<6; i++ {
            var h [5]byte
            if _,e=io.ReadFull(direct,h[:]); e!=nil {serverResult<-e; return}
            n:=int(binary.BigEndian.Uint16(h[3:5]))
            if n!=1355 || !bytes.Equal(h[:3], []byte{0x17,0x03,0x03}) {
                serverResult<-errors.New("post-handshake record head");return
            }
            wire := append([]byte{},h[:]...)
            wire = append(wire, make([]byte,n)...)
            if _,e=io.ReadFull(direct,wire[5:]);e!=nil {serverResult<-e;return}
            original, pn, e:=open(wire,i>=2,i>=4)
            if e!=nil || pn!=uint64(i) || !bytes.Equal(original,expected) {
                serverResult<-errors.New("post-handshake roundtrip mismatch");return
            }
        }
        serverResult <- nil
    }()
    raw,err:=net.DialTimeout("tcp",address,5*time.Second)
    if err!=nil {return err}
    defer raw.Close()
    if err=raw.SetDeadline(time.Now().Add(15*time.Second));err!=nil {return err}
    tc:=tls.Client(raw, ccfg)
    if err=tc.Handshake();err!=nil {return err}
    if tc.ConnectionState().Version!=tls.VersionTLS13 || len(tc.ConnectionState().PeerCertificates)==0 {
        return errors.New("client TLS handshake/authentication failed")
    }
    if _,err=tc.Write([]byte("C_READY"));err!=nil {return fmt.Errorf("client encrypted ready write: %w",err)}
    var ack [7]byte
    if _,err=io.ReadFull(tc,ack[:]);err!=nil {return fmt.Errorf("client encrypted ready read: %w",err)}
    if string(ack[:])!="S_READY" {return errors.New("bad peer TLS-ready marker")}
    direct:=tc.NetConn()
    for i:=0;i<6;i++ {
        rec:=seal(expected,i>=2,i>=4,uint64(i))
        if _,err=direct.Write(rec);err!=nil {return err}
        time.Sleep(45*time.Millisecond)
    }
    if err=<-serverResult;err!=nil {return err}
    fmt.Println("{\"tls13_mutually_authenticated_handshake\":true,\"post_handshake_direct_tcp_records\":6,\"inner_ipv4_roundtrip\":true,\"scope\":\"REAL_TLS_HANDSHAKE_FIXTURE_NOT_WBD_GO_TUN\",\"cryptographic_security_of_data_records\":\"NONE\"}")
    // Deliberately close the underlying connection without TLS close_notify.
    return nil
}
func main() {
    if len(os.Args)!=2 {panic("usage: go run tools/lan_xor_tlslike_tls_handoff.go PORT")}
    port,e:=strconv.Atoi(os.Args[1]);errf(e)
    errf(run(port))
}
