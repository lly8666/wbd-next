package realityfront

import (
 "context"
 "crypto/tls"
 "errors"
 "io"
 "net"
 "sync/atomic"
 "testing"
 "time"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// Exact V4 proof using the old pinned project's real P2 TLS decoy fixture.
// No second ClientHello parse in product, no fake/unauthenticated Rust epoch.
func TestH2209V4OrdinaryBrowserFallbackSameAssociation(t *testing.T) {
	cert := makeServerCert(t)
	serverRouteKey := []byte("0123456789abcdef0123456789abcdef")
	clientRouteKey := []byte("fedcba9876543210fedcba9876543210")
	assoc, peer := newAssociationPeer(t)
	defer assoc.Close()
	defer peer.Close()

	targetDial, targetServer := net.Pipe()
	var dialCalls atomic.Int32
	capturedHello := make(chan []byte, 1)
	targetDone := make(chan error, 1)
	go func() {
		defer targetServer.Close()
		info, raw, err := readClientHello(targetServer, 64<<10, 3*time.Second)
		if err != nil {
			targetDone <- err
			return
		}
		if info.ServerName != "target.test" {
			targetDone <- errors.New("decoy saw wrong SNI")
			return
		}
		capturedHello <- append([]byte(nil), raw...)

		tlsConn := tls.Server(replay(targetServer, raw), &tls.Config{
			Certificates: []tls.Certificate{cert},
			MinVersion:   tls.VersionTLS13,
			MaxVersion:   tls.VersionTLS13,
		})
		if err := tlsConn.HandshakeContext(context.Background()); err != nil {
			targetDone <- err
			return
		}
		var request [4]byte
		if _, err := io.ReadFull(tlsConn, request[:]); err != nil {
			targetDone <- err
			return
		}
		if string(request[:]) != "ping" {
			targetDone <- errors.New("decoy application request mismatch")
			return
		}
		if _, err := tlsConn.Write([]byte("pong")); err != nil {
			targetDone <- err
			return
		}
		targetDone <- tlsConn.Close()
	}()

	type serverResult struct {err error}
	serverDone := make(chan serverResult, 1)
	go func() {
        store,_:=NewV4EpochStore(4)
        _,err:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
            TLS: ServerConfig{
                ServerName:"target.test",RouteKey:serverRouteKey,
                TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},
                Timeout:3*time.Second,
            },
            ExpectedUsername:"solo",ExpectedPassword:"correct-password",
            ServerLimit:1450,
        },V4ServerOptions{DataPlaneReady:true,Epochs:store,Fallback:&FallbackConfig{
            Target:"decoy.invalid:443",ServerName:"target.test",
            SessionTimeout:5*time.Second,MaxBytes:1<<20,
            DialContext:func(context.Context,string,string)(net.Conn,error){
                dialCalls.Add(1);return targetDial,nil
            },
        }})
        serverDone<-serverResult{err:err}
    }()

	clientTLS, err := newFirefox120Client(peer, ClientConfig{
		ServerName: "target.test",
		RouteKey:   clientRouteKey,
		Timeout:    3 * time.Second,
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := clientTLS.HandshakeContext(context.Background()); err != nil {
		t.Fatal(err)
	}
	if _, err := clientTLS.Write([]byte("ping")); err != nil {
		t.Fatal(err)
	}
	var response [4]byte
	if _, err := io.ReadFull(clientTLS, response[:]); err != nil {
		t.Fatal(err)
	}
	if string(response[:]) != "pong" {
		t.Fatalf("response=%q", response)
	}
	// The decoy closes first after pong. Let the TLS client consume its
	// close_notify before closing the underlying test transport; this Read also
	// drives the FakeTCP peer's cumulative ACK exactly as a kernel TCP stack
	// would continue doing while the TLS session shuts down.
	_ = clientTLS.SetReadDeadline(time.Now().Add(time.Second))
	var afterClose [1]byte
	if n, err := clientTLS.Read(afterClose[:]); n != 0 || !errors.Is(err, io.EOF) {
		t.Fatalf("fallback TLS shutdown: n=%d err=%v want EOF", n, err)
	}
	_ = clientTLS.SetReadDeadline(time.Time{})
	// The application has consumed the decoy's TLS close and now half-closes its
	// TCP send side. This lets the opposite fallback copy drain without relying
	// on the old full-close workaround.
	if err := peer.CloseWrite(); err != nil {
		t.Fatal(err)
	}

	if err := <-targetDone; err != nil && !errors.Is(err, net.ErrClosed) && !errors.Is(err, io.ErrClosedPipe) {
		t.Fatal(err)
	}
	var sr serverResult
	select {
	case sr = <-serverDone:
	case <-time.After(2 * time.Second):
		t.Fatal("fallback splice did not terminate after target close")
	}
	_ = clientTLS.Close()
	_ = peer.Close()
	if !errors.Is(sr.err,ErrV4FallbackHandled) {
        t.Fatalf("V4 ordinary browser must finish decoy only: %v",sr.err)
    }
	if dialCalls.Load() != 1 {
		t.Fatalf("dial calls=%d want=1", dialCalls.Load())
	}
	gotTargetHello := <-capturedHello
	if len(gotTargetHello)<32 || !recognized(gotTargetHello,clientRouteKey,"target.test") ||
       recognized(gotTargetHello,serverRouteKey,"target.test") {
        t.Fatal("decoy ClientHello was not the byte-exact non-WBD real TLS original")
    }
	if _, ok := assoc.TransitionState(); ok {
		t.Fatal("fallback path prepared a record transition")
	}
}



func TestH2209V4RecognizedNeverDialsDecoy(t *testing.T) {
 cert:=makeServerCert(t)
 key:=[]byte("0123456789abcdef0123456789abcdef")
 assoc,peer:=newAssociationPeer(t)
 defer assoc.Close();defer peer.Close()
 store,_:=NewV4EpochStore(4)
 var dialCalls atomic.Int32
 done:=make(chan error,1)
 go func(){
    session,err:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
        TLS:ServerConfig{ServerName:"target.test",RouteKey:key,
            TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
        ExpectedUsername:"solo",ExpectedPassword:"secret",ServerLimit:1400,
    },V4ServerOptions{DataPlaneReady:true,Epochs:store,Fallback:&FallbackConfig{
        Target:"decoy.invalid:443",ServerName:"target.test",
        DialContext:func(context.Context,string,string)(net.Conn,error){
            dialCalls.Add(1);return nil,errors.New("recognized WBD must never dial decoy")
        },
    }})
    if err==nil && session==nil{err=errors.New("missing protected V4 server session")}
    done<-err
 }()
 client,err:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
    TLS:ClientConfig{ServerName:"target.test",RouteKey:key,
        RootCAs:v4TestRoots(cert),Timeout:3*time.Second},
    Username:"solo",Password:"secret",TunnelID:[]byte("0123456789abcdef"),
    ClientLimit:1400,DesiredLanes:1,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
 },V4ClientOptions{DataPlaneReady:true})
 if err!=nil||client==nil {t.Fatalf("WBD protected client rejected: %v",err)}
 select{
 case err=<-done:if err!=nil{t.Fatalf("WBD protected server rejected: %v",err)}
 case <-time.After(4*time.Second):t.Fatal("WBD admission blocked by decoy")
 }
 if dialCalls.Load()!=0{t.Fatal("recognized WBD incorrectly dialed decoy")}
 if state,ok:=assoc.TransitionState();!ok||state!=faketcp.TransitionDetached{
    t.Fatalf("recognized WBD did not detach into original protected owner state=%v exists=%v",state,ok)
 }
}


func TestH2209V4WrongSNIRefusesToDialDecoy(t *testing.T){
 assoc,peer:=newAssociationPeer(t)
 defer assoc.Close();defer peer.Close()
 store,_:=NewV4EpochStore(4)
 serverKey:=[]byte("0123456789abcdef0123456789abcdef")
 wrongKey:=[]byte("fedcba9876543210fedcba9876543210")
 var dials atomic.Int32
 done:=make(chan error,1)
 go func(){
    _,err:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
        TLS:ServerConfig{ServerName:"target.test",RouteKey:serverKey,Timeout:3*time.Second},
        ExpectedUsername:"solo",ExpectedPassword:"secret",ServerLimit:1400,
    },V4ServerOptions{DataPlaneReady:true,Epochs:store,Fallback:&FallbackConfig{
        Target:"decoy.invalid:443",ServerName:"target.test",
        DialContext:func(context.Context,string,string)(net.Conn,error){dials.Add(1);return nil,errors.New("wrong SNI dialed")},
    }})
    done<-err
 }()
 client,err:=newFirefox120Client(peer,ClientConfig{
    ServerName:"wrong.test",RouteKey:wrongKey,Timeout:3*time.Second,
 })
 if err!=nil{t.Fatal(err)}
 handshake:=make(chan error,1)
 go func(){handshake<-client.HandshakeContext(context.Background())}()
 select{
 case err=<-done:
     if err==nil||!errors.Is(err,ErrV4FallbackHandled){t.Fatalf("wrong SNI not handled as rejected decoy: %v",err)}
 case <-time.After(4*time.Second):t.Fatal("wrong SNI classification blocked")
 }
 assoc.Close();_ = peer.Close()
 select{case <-handshake:case <-time.After(3*time.Second):t.Fatal("wrong SNI client did not terminate")}
 if dials.Load()!=0{t.Fatal("wrong-SNI client dialed decoy")}
 if _,ok:=assoc.TransitionState();ok{t.Fatal("wrong SNI allocated protected transition")}
}
