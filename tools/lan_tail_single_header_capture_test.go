// The actual sealed wire is written through real TCP sockets on loopback
// while tcpdump captures lo. Standard Go TLS1.3 is sent on a second port.
// This is a loopback TCP capture, not an independent LAN two-host capture.
package tailone

import (
 "bytes"
 "crypto/ecdsa"
 "crypto/elliptic"
 "crypto/rand"
 "crypto/tls"
 "crypto/x509"
 "crypto/x509/pkix"
 "encoding/binary"
 "errors"
 "io"
 "math/big"
 "net"
 "os"
 "testing"
 "time"
)

const captureCustomPort="127.0.0.1:38443"
const captureRealTLSPort="127.0.0.1:38444"
const captureRecords=100
const referenceTLSRecords=30

func writeFull(c net.Conn,b []byte)error{
 for len(b)>0{
  n,err:=c.Write(b)
  if err!=nil{return err}
  if n==0{return io.ErrShortWrite}
  b=b[n:]
 }
 return nil
}
func runCustomSocketCapture(t *testing.T){
 listener,err:=net.Listen("tcp4",captureCustomPort)
 if err!=nil{t.Fatalf("listen custom capture port: %v",err)}
 defer listener.Close()
 done:=make(chan error,1)
 go func(){
  incoming,e:=listener.Accept()
  if e!=nil{done<-e;return}
  defer incoming.Close()
  _=incoming.SetDeadline(time.Now().Add(20*time.Second))
  c:=newSession()
  f:=innerTLSFixture()
  other:=otherFixture(f.record)
  var hdr [5]byte
  var wire [1600]byte
  var out [1600]byte
  for i:=0;i<captureRecords;i++{
   if _,e=io.ReadFull(incoming,hdr[:]);e!=nil{done<-e;return}
   if hdr[0]!=0x17||hdr[1]!=3||hdr[2]!=3{
    done<-errors.New("actual capture record has wrong TLS-like prefix");return
   }
   n:=int(binary.BigEndian.Uint16(hdr[3:5]))
   if n>len(wire)-5||n<3{
    done<-errors.New("invalid real TCP record size");return
   }
   copy(wire[:5],hdr[:])
   if _,e=io.ReadFull(incoming,wire[5:5+n]);e!=nil{done<-e;return}
   counter:=uint64(i+1)
   mode,got,e:=c.open(wire[:5+n],out[:],counter,tailLast8Word,false)
   if e!=nil{done<-e;return}
   want,retrans,wantAES:=inputFor(i,80,f.record,other)
   if mode!=wantAES||!bytes.Equal(got,want){
    done<-errors.New("TCP peer did not recover exact original TLS/nonTLS data");return
   }
   if !wantAES{
    plaintext,e2:=f.decrypt(got)
    if e2!=nil||!bytes.Equal(plaintext,f.original){
     done<-errors.New("original inner TLS AEAD tag invalid after TCP transit");return
    }
   }
   _=retrans
  }
  done<-nil
 }()
 sender,err:=net.DialTimeout("tcp4",captureCustomPort,5*time.Second)
 if err!=nil{t.Fatal(err)}
 if tcp,ok:=sender.(*net.TCPConn);ok{_ = tcp.SetNoDelay(true)}
 _=sender.SetDeadline(time.Now().Add(20*time.Second))
 s:=newSession()
 f:=innerTLSFixture()
 other:=otherFixture(f.record)
 var tx [1600]byte
 var fastCount,aesCount,bytesOut int
 for i:=0;i<captureRecords;i++{
  inner,retrans,wantAES:=inputFor(i,80,f.record,other)
  wire:=s.seal(tx[:],inner,retrans,true,uint64(i+1),tailLast8Word,false,false)
  if len(wire)!=recordBytes+markerLen && !wantAES{
   t.Fatal("unexpected fast wire length")
  }
  if err=writeFull(sender,wire);err!=nil{t.Fatal(err)}
  bytesOut+=len(wire)
  if wantAES{aesCount++}else{fastCount++}
  time.Sleep(3*time.Millisecond)
 }
 _=sender.Close()
 select{
 case e:=<-done:
  if e!=nil{t.Fatalf("custom TCP receiver: %v",e)}
 case <-time.After(20*time.Second):
  t.Fatal("TCP capture receiver timed out")
 }
 t.Logf("CAPTURE_CUSTOM_PASS records=%d fast=%d aes=%d total_application_wire_bytes=%d fast_wire=%d aes_wire=%d tcp_port=38443 real_tcp_io=true",captureRecords,fastCount,aesCount,bytesOut,recordBytes+2,recordBytes+23)
}
func tlsTestCertificate(t *testing.T)tls.Certificate{
 private,e:=ecdsa.GenerateKey(elliptic.P256(),rand.Reader)
 if e!=nil{t.Fatal(e)}
 tmpl:=&x509.Certificate{
  SerialNumber:big.NewInt(20261026),
  Subject:pkix.Name{CommonName:"wbd-loopback-tls13-baseline.invalid"},
  NotBefore:time.Now().Add(-1*time.Hour),
  NotAfter:time.Now().Add(time.Hour),
  DNSNames:[]string{"localhost"},
  KeyUsage:x509.KeyUsageDigitalSignature,
  ExtKeyUsage:[]x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
  BasicConstraintsValid:true,
 }
 der,e:=x509.CreateCertificate(rand.Reader,tmpl,tmpl,&private.PublicKey,private)
 if e!=nil{t.Fatal(e)}
 return tls.Certificate{Certificate:[][]byte{der},PrivateKey:private}
}
func runTrueTLS13Reference(t *testing.T){
 cert:=tlsTestCertificate(t)
 listener,e:=tls.Listen("tcp4",captureRealTLSPort,&tls.Config{
  MinVersion:tls.VersionTLS13, MaxVersion:tls.VersionTLS13,
  Certificates:[]tls.Certificate{cert},
 })
 if e!=nil{t.Fatal(e)}
 defer listener.Close()
 done:=make(chan error,1)
 go func(){
  conn,e:=listener.Accept()
  if e!=nil{done<-e;return}
  defer conn.Close()
  _=conn.SetDeadline(time.Now().Add(20*time.Second))
  buf:=make([]byte,recordBytes)
  for i:=0;i<referenceTLSRecords;i++{
   if _,e=io.ReadFull(conn,buf);e!=nil{done<-e;return}
   if buf[0]!=byte(i){done<-errors.New("true TLS application body differs");return}
  }
  done<-nil
 }()
 client,e:=tls.DialWithDialer(&net.Dialer{Timeout:5*time.Second},
  "tcp4",captureRealTLSPort,&tls.Config{MinVersion:tls.VersionTLS13,
  MaxVersion:tls.VersionTLS13,
  InsecureSkipVerify:true, // local testing certificate only; not production
  ServerName:"localhost"})
 if e!=nil{t.Fatalf("reference TLS handshake: %v",e)}
 if client.ConnectionState().Version!=tls.VersionTLS13{t.Fatal("TLS reference not negotiated version1.3")}
 if tcp,ok:=client.NetConn().(*net.TCPConn);ok{_ = tcp.SetNoDelay(true)}
 _=client.SetDeadline(time.Now().Add(20*time.Second))
 app:=make([]byte,recordBytes)
 for i:=0;i<referenceTLSRecords;i++{
  app[0]=byte(i)
  for j:=1;j<len(app);j++{app[j]=byte((j*11+i*3)%256)}
  if e=writeFull(client,app);e!=nil{t.Fatal(e)}
  time.Sleep(3*time.Millisecond)
 }
 _=client.Close()
 select{
 case err:=<-done:
  if err!=nil{t.Fatalf("true TLS reference peer: %v",err)}
 case <-time.After(20*time.Second):
  t.Fatal("true TLS receiver timeout")
 }
 t.Logf("CAPTURE_TLS13_REFERENCE_PASS negotiation=true app_records=%d app_bytes=%d tcp_port=38444 real_tcp_io=true",referenceTLSRecords,referenceTLSRecords*recordBytes)
}
func TestLoopbackPacketCapture(t *testing.T){
 if os.Getenv("WBD_PACKET_CAPTURE")!="1"{t.Skip("requires external tcpdump on lo; controlled CI only")}
 runCustomSocketCapture(t)
 runTrueTLS13Reference(t)
}
