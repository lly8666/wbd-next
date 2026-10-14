package realityfront

import (
    "bytes"
    "context"
    "crypto/tls"
    "errors"
    "testing"
    "time"
)

func v4TestPolicy(lanes uint8, cipher uint8) AdmissionPolicy {
    p:=AdmissionPolicy{
        Schema:PolicySchemaV3,Transport:TransportNormal,DesiredLanes:lanes,
        FECMode:FECFixed,FixedParity:4,Cipher:cipher,
    }
    if lanes>1 {p.Transport=TransportGame}
    return p
}

func v4Pair(t *testing.T,store *V4EpochStore,user string,tunnel []byte,lane uint8,policy AdmissionPolicy,epoch [16]byte)(*V4ClientSession,*V4ServerSession,error,error) {
    t.Helper()
    cert:=makeServerCert(t)
    key:=[]byte("0123456789abcdef0123456789abcdef")
    assoc,peer:=newAssociationPeer(t)
    defer assoc.Close()
    defer peer.Close()
    type answer struct { s *V4ServerSession; err error }
    server:=make(chan answer,1)
    go func() {
        s,e:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
            TLS:ServerConfig{ServerName:"target.test",RouteKey:key,
                TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
            ExpectedUsername:user,ExpectedPassword:"secret",ServerLimit:1400,
        },V4ServerOptions{DataPlaneReady:true,Epochs:store})
        server<-answer{s,e}
    }()
    client,clientErr:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
        TLS:ClientConfig{ServerName:"target.test",RouteKey:key,Timeout:3*time.Second},
        Username:user,Password:"secret",TunnelID:bytes.Clone(tunnel),
        ClientLimit:1400,LaneID:lane,Policy:policy,
    },V4ClientOptions{DataPlaneReady:true,Epoch:epoch})
    select {
    case s:= <-server:
        return client,s.s,clientErr,s.err
    case <-time.After(5*time.Second):
        t.Fatal("V4 real TLS server timeout")
        return nil,nil,nil,nil
    }
}

func TestR0V4ActualProtectedPeerHandshakeAllCiphers(t *testing.T) {
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256} {
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(4)
            if err!=nil{t.Fatal(err)}
            tunnel:=[]byte("0123456789abcdef")
            client,server,ce,se:=v4Pair(t,store,"solo",tunnel,1,v4TestPolicy(1,cipher),[16]byte{})
            if ce!=nil||se!=nil{t.Fatalf("client=%v server=%v",ce,se)}
            if client.Epoch==[16]byte{}||client.Epoch!=server.Epoch {
                t.Fatal("different logical epochs or zero epoch")
            }
            if client.Negotiated.RecordVersion!=4||server.Negotiated.RecordVersion!=4 ||
               client.Negotiated.Keys!=server.Negotiated.Keys ||
               client.Negotiated.Keys.C2S==client.Negotiated.Keys.S2C {
                t.Fatal("V4 real protected exporter/keys mismatch")
            }
            if err:=store.ReleaseLane("solo",tunnel,1,client.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}

func TestR0V4LaneJoinEpochAndDuplicateRejected(t *testing.T) {
    store,_:=NewV4EpochStore(3)
    tunnel:=[]byte("abcdef0123456789")
    policy:=v4TestPolicy(2,CipherChaCha)
    c1,s1,e1,f1:=v4Pair(t,store,"alice",tunnel,1,policy,[16]byte{})
    if e1!=nil||f1!=nil{t.Fatalf("first lane %v %v",e1,f1)}
    c2,s2,e2,f2:=v4Pair(t,store,"alice",tunnel,2,policy,c1.Epoch)
    if e2!=nil||f2!=nil{t.Fatalf("join lane %v %v",e2,f2)}
    if c2.Epoch!=c1.Epoch||s2.Epoch!=s1.Epoch{t.Fatal("join changed epoch")}
    _,_,ce,se:=v4Pair(t,store,"alice",tunnel,2,policy,c1.Epoch)
    if !errors.Is(ce,ErrAdmissionParams)||!errors.Is(se,ErrAdmissionParams) {
        t.Fatalf("duplicate lane should be rejected, client=%v server=%v",ce,se)
    }
    _,_,ce,se=v4Pair(t,store,"alice",tunnel,1,policy,[16]byte{})
    if !errors.Is(ce,ErrAdmissionParams)||!errors.Is(se,ErrAdmissionParams) {
        t.Fatalf("zero epoch tried to overwrite active tunnel, client=%v server=%v",ce,se)
    }
    if err:=store.ReleaseLane("alice",tunnel,2,c2.Epoch);err!=nil{t.Fatal(err)}
    if err:=store.ReleaseLane("alice",tunnel,1,c1.Epoch);err!=nil{t.Fatal(err)}
    c3,_,ce,se:=v4Pair(t,store,"alice",tunnel,1,policy,[16]byte{})
    if ce!=nil||se!=nil{t.Fatalf("explicit released restart %v %v",ce,se)}
    if c3.Epoch==c1.Epoch {t.Fatal("new logical tunnel reused epoch")}
    if err:=store.ReleaseLane("alice",tunnel,1,c3.Epoch);err!=nil{t.Fatal(err)}
}

func TestR0V4WrongEpochAndIdentityReject(t *testing.T) {
    store,_:=NewV4EpochStore(2)
    tunnel:=[]byte("0123456789abcdef")
    var wrong [16]byte
    wrong[0]=0x25
    _,_,ce,se:=v4Pair(t,store,"solo",tunnel,1,v4TestPolicy(1,CipherChaCha),wrong)
    if !errors.Is(ce,ErrAdmissionParams)||!errors.Is(se,ErrAdmissionParams) {
        t.Fatalf("unknown epoch accepted: %v %v",ce,se)
    }
    c,_,ce,se:=v4Pair(t,store,"solo",tunnel,1,v4TestPolicy(1,CipherChaCha),[16]byte{})
    if ce!=nil||se!=nil{t.Fatalf("normal start failed %v %v",ce,se)}
    // A known epoch cannot bind to another authenticated username.
    _,_,ce,se=v4Pair(t,store,"other",tunnel,2,v4TestPolicy(2,CipherChaCha),c.Epoch)
    if !errors.Is(ce,ErrAdmissionParams)||!errors.Is(se,ErrAdmissionParams) {
        t.Fatalf("cross-user epoch admitted %v %v",ce,se)
    }
    if err:=store.ReleaseLane("solo",tunnel,1,c.Epoch);err!=nil{t.Fatal(err)}
}

func TestR0V4FeatureGateAndBoundedStore(t *testing.T) {
    if _,err:=NewV4EpochStore(0);!errors.Is(err,ErrAdmissionParams){t.Fatal("unbounded store accepted")}
    store,_:=NewV4EpochStore(1)
    if _,err:=EstablishClientV4(context.Background(),nil,ClientAdmissionConfig{},V4ClientOptions{DataPlaneReady:false});!errors.Is(err,ErrAdmissionUnsupported){
        t.Fatal("V4 client advertised without engine")
    }
    if _,err:=EstablishServerV4(context.Background(),nil,ServerAdmissionConfig{},V4ServerOptions{DataPlaneReady:false,Epochs:store});!errors.Is(err,ErrAdmissionUnsupported){
        t.Fatal("V4 server advertised without engine")
    }
    p:=v4TestPolicy(1,CipherChaCha)
    _=p
    var zero [16]byte
    if _,err:=v4Encode(V4Extension{Features:1,Epoch:zero});!errors.Is(err,ErrAdmissionUnsupported){t.Fatalf("partial feature accepted: %v",err)}
    wire,err:=v4Encode(V4Extension{Features:3,Epoch:zero})
    if err!=nil{t.Fatal(err)}
    wire[23]=1
    if _,err:=v4Decode(wire[:]);!errors.Is(err,ErrAdmissionParams){t.Fatalf("invalid reserved accepted: %v",err)}
}

func TestR0V4OldGoV3RejectsActualTLSUpgrade(t *testing.T) {
    cert:=makeServerCert(t)
    key:=[]byte("0123456789abcdef0123456789abcdef")
    assoc,peer:=newAssociationPeer(t)
    defer assoc.Close()
    defer peer.Close()
    type serverAnswer struct { err error }
    ch:=make(chan serverAnswer,1)
    go func(){
        _,err:=EstablishServer(context.Background(),assoc,ServerAdmissionConfig{
            TLS:ServerConfig{ServerName:"target.test",RouteKey:key,
                TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
            ExpectedUsername:"solo",ExpectedPassword:"secret",ServerLimit:1400,RequireV3:true,
        })
        ch<-serverAnswer{err}
    }()
    _,clientErr:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
        TLS:ClientConfig{ServerName:"target.test",RouteKey:key,Timeout:3*time.Second},
        Username:"solo",Password:"secret",TunnelID:[]byte("0123456789abcdef"),
        ClientLimit:1400,Policy:v4TestPolicy(1,CipherChaCha),
    },V4ClientOptions{DataPlaneReady:true})
    select{
    case response:= <-ch:
        if !errors.Is(clientErr,ErrAdmissionVersion)||!errors.Is(response.err,ErrAdmissionVersion) {
            t.Fatalf("old V3 side did not reject V4: client=%v server=%v",clientErr,response.err)
        }
    case <-time.After(5*time.Second):t.Fatal("legacy TLS rejection timeout")
    }
}
