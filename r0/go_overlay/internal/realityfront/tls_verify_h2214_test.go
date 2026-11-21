package realityfront

import (
    "context"
    "crypto/tls"
    "crypto/x509"
    "net"
    "testing"
    "time"
)

// Exercises the actual original-Go Firefox120 TLS handshake with a self-signed
// server, not only the CLI flag parser. No external network or TLS bypass.
func TestH2214ClientTLSCertificateValidationPolicy(t *testing.T) {
    cert:=makeServerCert(t) // pinned original-Go TLS test fixture, SAN target.test
    leaf,err:=x509.ParseCertificate(cert.Certificate[0])
    if err!=nil {t.Fatal(err)}
    trusted:=x509.NewCertPool()
    trusted.AddCert(leaf)
    for _,tc:=range []struct{name string;verify bool;roots *x509.CertPool;success bool}{
        {"legacy-default-no-validation",false,nil,true},
        {"opt-in-reject-self-signed-untrusted",true,nil,false},
        {"opt-in-accept-private-trusted-root",true,trusted,true},
    }{
        t.Run(tc.name,func(t *testing.T) {
            client,server:=net.Pipe()
            defer client.Close()
            defer server.Close()
            ctx,cancel:=context.WithTimeout(context.Background(),7*time.Second)
            defer cancel()
            completed:=make(chan error,1)
            go func(){
                endpoint:=tls.Server(server,&tls.Config{
                    Certificates:[]tls.Certificate{cert},
                    MinVersion:tls.VersionTLS13,
                    MaxVersion:tls.VersionTLS13,
                    SessionTicketsDisabled:true,
                })
                completed<-endpoint.HandshakeContext(ctx)
            }()
            route:=[]byte("0123456789abcdef0123456789abcdef")
            handshake,err:=handshakeClientConn(ctx,client,ClientConfig{
                ServerName:"target.test", RouteKey:route, VerifyServer:tc.verify,
                RootCAs:tc.roots,Timeout:5*time.Second,
            })
            if (err==nil)!=tc.success {t.Fatalf("handshake err=%v success=%v want=%v",err,err==nil,tc.success)}
            if handshake!=nil {_=handshake.Close()}
            _=client.Close()
            select {case <-completed:case <-ctx.Done():t.Fatal("TLS server handshake did not terminate")}
        })
    }
}
