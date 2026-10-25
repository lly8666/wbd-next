package realityfront

import (
    "bytes"
    "crypto/sha256"
    "encoding/binary"
    "os"
    "context"
    "crypto/tls"
    "errors"
    "io"
    "github.com/lly8666/wobuzhidao/internal/faketcp"
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
    return v4PairFeatureProbe(t,store,user,tunnel,lane,policy,epoch,false,false)
}
func v4PairFeatureProbe(t *testing.T,store *V4EpochStore,user string,tunnel []byte,lane uint8,policy AdmissionPolicy,epoch [16]byte,clientFec2,serverFec2 bool)(*V4ClientSession,*V4ServerSession,error,error) {
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
        },V4ServerOptions{DataPlaneReady:true,Epochs:store,fec2ProbeOnly:serverFec2})
        server<-answer{s,e}
    }()
    client,clientErr:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
        TLS:ClientConfig{ServerName:"target.test",RouteKey:key,Timeout:3*time.Second},
        Username:user,Password:"secret",TunnelID:bytes.Clone(tunnel),
        ClientLimit:1400,LaneID:lane,Policy:policy,
    },V4ClientOptions{DataPlaneReady:true,Epoch:epoch,fec2ProbeOnly:clientFec2})
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

// This V4 private extension byte was reserved in all off-mode records.
// A Game+FEC server may never turn a requested fixed profile into another,
// and a legacy feature3 peer cannot accept a fixed FEC profile silently.
func TestFECGameProtectedV4ProfileWireOffAndFailClosed(t *testing.T){
    var epoch [16]byte;epoch[0]=17
    off:=V4Extension{Features:v4RequiredFeatures|v4FeatureFEC2,Epoch:epoch}
    wire,err:=v4Encode(off)
    if err!=nil{t.Fatal(err)}
    if wire[21]!=0||wire[22]!=0||wire[23]!=0{
        t.Fatal("off-mode must remain byte-for-byte old V4 extension")
    }
    for profile:=uint8(1);profile<=7;profile++{
        choice:=V4Extension{Features:v4RequiredFeatures|v4FeatureFEC2,
            Epoch:epoch,GameFec:profile}
        raw,e:=v4Encode(choice)
        if e!=nil{t.Fatal(e)}
        decoded,e:=v4Decode(raw[:])
        if e!=nil||decoded!=choice{t.Fatalf("auth extension=%d got=%+v err=%v",profile,decoded,e)}
        raw[21]=8
        if _,e=v4Decode(raw[:]);!errors.Is(e,ErrAdmissionParams){
            t.Fatalf("out-of-range fixed profile %d not denied: %v",profile,e)
        }
    }
    if _,err=v4Encode(V4Extension{
        Features:v4RequiredFeatures,Epoch:epoch,GameFec:7,
    });!errors.Is(err,ErrAdmissionUnsupported){t.Fatalf("feature3 admitted GameFEC: %v",err)}
    raw,_:=v4Encode(V4Extension{Features:v4RequiredFeatures,Epoch:epoch})
    raw[21]=1
    if _,err=v4Decode(raw[:]);!errors.Is(err,ErrAdmissionUnsupported){
        t.Fatalf("legacy mode accepted forged Game fixed profile: %v",err)
    }
    raw,_=v4Encode(off);raw[22]=1
    if _,err=v4Decode(raw[:]);!errors.Is(err,ErrAdmissionParams){
        t.Fatalf("nonzero still-reserved byte accepted: %v",err)
    }
    store,_:=NewV4EpochStore(2)
    if _,err=EstablishServerV4(context.Background(),nil,ServerAdmissionConfig{},
        V4ServerOptions{DataPlaneReady:true,Epochs:store,GameFec:8});
        !errors.Is(err,ErrAdmissionUnsupported){
        t.Fatalf("invalid server GameFEC accepted: %v",err)
    }
    if _,err=EstablishClientV4(context.Background(),nil,ClientAdmissionConfig{},
        V4ClientOptions{DataPlaneReady:true,GameFec:1});
        !errors.Is(err,ErrAdmissionUnsupported){
        t.Fatalf("non-native GameFEC client grant accepted: %v",err)
    }
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


func TestR0V4ColdSnapshotActualAuthenticatedTLSAllCiphers(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        store,err:=NewV4EpochStore(2)
        if err!=nil{t.Fatal(err)}
        tunnel:=[]byte("0123456789abcdef")
        c,s,ce,se:=v4Pair(t,store,"cold-user",tunnel,1,v4TestPolicy(1,cipher),[16]byte{})
        if ce!=nil||se!=nil{t.Fatalf("TLS peer failed cipher %d: %v %v",cipher,ce,se)}
        cc,e:=c.ColdSnapshot();if e!=nil{t.Fatal(e)}
        ss,e:=s.ColdSnapshot();if e!=nil{t.Fatal(e)}
        if cc.ServerSide()||!ss.ServerSide()||cc.Principal()!="cold-user"||ss.Principal()!="cold-user" ||
           cc.TunnelID()!=ss.TunnelID()||cc.Epoch()!=ss.Epoch()||
           cc.Incarnation()!=ss.Incarnation()||cc.LaneID()!=1||ss.LaneID()!=1 ||
           cc.Cipher()!=cipher||ss.Cipher()!=cipher||
           cc.DirectionKeys()!=ss.DirectionKeys()||cc.DirectionKeys().C2S==cc.DirectionKeys().S2C {
            t.Fatalf("protected snapshot lost identity/direction/cipher: %d",cipher)
        }
        if a,b:=cc.RecordLimits();a!=1400||b!=1400 {t.Fatalf("limits %d %d",a,b)}
        if cc.Epoch()==[16]byte{} {t.Fatal("no authenticated epoch")}
        // Caller mutation cannot rewrite snapshot's fixed, private fields.
        copied:=cc.TunnelID();copied[0]^=0xff
        if cc.TunnelID()!=ss.TunnelID(){t.Fatal("snapshot tunnel aliases caller")}
        keyCopy:=cc.DirectionKeys();keyCopy.C2S.AEADKey[0]^=0xff
        if cc.DirectionKeys()!=ss.DirectionKeys(){t.Fatal("snapshot keys alias caller")}
        c.Negotiated.TunnelID[0]^=0xff
        if cc.TunnelID()!=ss.TunnelID(){t.Fatal("snapshot borrowed Go session storage")}
        if err:=store.ReleaseLane("cold-user",tunnel,1,ss.Epoch());err!=nil{t.Fatal(err)}
    }
}
func TestR0V4ColdSnapshotNilForgedAndMutatedSessionDenied(t *testing.T){
    var client *V4ClientSession
    if _,err:=client.ColdSnapshot();!errors.Is(err,ErrAdmissionUnsupported){t.Fatal(err)}
    var server *V4ServerSession
    if _,err:=server.ColdSnapshot();!errors.Is(err,ErrAdmissionUnsupported){t.Fatal(err)}
    if _,err:=(&V4ClientSession{}).ColdSnapshot();!errors.Is(err,ErrAdmissionUnsupported){t.Fatal(err)}
    if _,err:=(&V4ServerSession{}).ColdSnapshot();!errors.Is(err,ErrAdmissionUnsupported){t.Fatal(err)}
    store,_:=NewV4EpochStore(1)
    tunnel:=[]byte("0123456789abcdef")
    c,s,ce,se:=v4Pair(t,store,"real",tunnel,1,v4TestPolicy(1,CipherChaCha),[16]byte{})
    if ce!=nil||se!=nil{t.Fatalf("TLS: %v %v",ce,se)}
    // Only the protected handshake path mints the private frozen witness.
    original:=c.Negotiated
    baseEpoch:=c.Epoch
    basePrincipal:=c.authenticatedPrincipal
    baseTLSKeys:=c.TLS.Keys
    baseline,err:=c.ColdSnapshot()
    if err!=nil{t.Fatal(err)}
    fake:=&V4ClientSession{
        ClientAdmissionSession:c.ClientAdmissionSession,Epoch:c.Epoch,
        coldAuthenticated:true,authenticatedPrincipal:c.authenticatedPrincipal,
    }
    if _,err:=fake.ColdSnapshot();!errors.Is(err,ErrAdmissionParams){
        t.Fatalf("self-asserted auth boolean minted a cold witness: %v",err)
    }
    cases:=[]func(){func(){c.Negotiated.RecordVersion=3},
        func(){c.Epoch=[16]byte{}},
        func(){c.Negotiated.LaneID=0},
        func(){c.Negotiated.TunnelID=[]byte{1}},
        func(){c.Negotiated.Keys.C2S=c.Negotiated.Keys.S2C},
        // These look grammatically valid but were never negotiated.
        func(){c.Negotiated.ClientLimit--},
        func(){c.Negotiated.ServerLimit--},
        func(){c.Negotiated.Policy.Cipher=CipherAES128},
        func(){c.Negotiated.IncarnationNonce[0]^=0xff},
        func(){c.Negotiated.Keys.C2S.AEADKey[0]^=0xff},
        func(){c.authenticatedPrincipal="imposter"},
        func(){c.TLS.Keys.C2S.IV[0]^=0xff}}
    for i,mutate:=range cases{
        c.Negotiated=original
        c.Epoch=baseEpoch
        c.authenticatedPrincipal=basePrincipal
        c.TLS.Keys=baseTLSKeys
        mutate()
        if _,err:=c.ColdSnapshot();!errors.Is(err,ErrAdmissionParams){
            t.Fatalf("post-auth client edit %d minted a cold witness: %v",i,err)
        }
    }
    c.Negotiated=original
    c.Epoch=baseEpoch
    c.authenticatedPrincipal=basePrincipal
    c.TLS.Keys=baseTLSKeys
    recovered,err:=c.ColdSnapshot()
    if err!=nil||recovered!=baseline{t.Fatalf("original cold witness not recovered: %v",err)}
    serverOriginal:=s.Negotiated
    serverTLSKeys:=s.TLS.Keys
    serverCold,err:=s.ColdSnapshot()
    if err!=nil{t.Fatal(err)}
    s.Negotiated.ServerLimit--
    if _,err:=s.ColdSnapshot();!errors.Is(err,ErrAdmissionParams){t.Fatalf("server limit edit: %v",err)}
    s.Negotiated=serverOriginal
    s.TLS.Keys.S2C.HPKey[0]^=0xff
    if _,err:=s.ColdSnapshot();!errors.Is(err,ErrAdmissionParams){t.Fatalf("server TLS key edit: %v",err)}
    s.TLS.Keys=serverTLSKeys
    if got,err:=s.ColdSnapshot();err!=nil||got!=serverCold{t.Fatalf("server freeze recovery: %v",err)}
    if err:=store.ReleaseLane("real",tunnel,1,s.Epoch);err!=nil{t.Fatal(err)}
}
func TestR0V4ColdSnapshotTunnelRotationDoesNotReuseEpochOrKeys(t *testing.T){
    store,_:=NewV4EpochStore(2)
    tunnel:=[]byte("abcdefghijklmnop")
    policy:=v4TestPolicy(2,CipherChaCha)
    c1,s1,ce,se:=v4Pair(t,store,"user",tunnel,1,policy,[16]byte{})
    if ce!=nil||se!=nil{t.Fatalf("first TLS %v %v",ce,se)}
    first,_:=c1.ColdSnapshot()
    joined,s2,ce,se:=v4Pair(t,store,"user",tunnel,2,policy,c1.Epoch)
    if ce!=nil||se!=nil{t.Fatalf("joined TLS %v %v",ce,se)}
    second,_:=joined.ColdSnapshot()
    if first.Epoch()!=second.Epoch()||first.LaneID()==second.LaneID()||
       first.DirectionKeys()==second.DirectionKeys()||
       first.Incarnation()==second.Incarnation(){t.Fatal("lane scopes aliased")}
    if err:=store.ReleaseLane("user",tunnel,2,s2.Epoch);err!=nil{t.Fatal(err)}
    if err:=store.ReleaseLane("user",tunnel,1,s1.Epoch);err!=nil{t.Fatal(err)}
    c3,s3,ce,se:=v4Pair(t,store,"user",tunnel,1,policy,[16]byte{})
    if ce!=nil||se!=nil{t.Fatalf("restart TLS %v %v",ce,se)}
    restarted,_:=c3.ColdSnapshot()
    if first.Epoch()==restarted.Epoch()||first.Incarnation()==restarted.Incarnation()||
       first.DirectionKeys()==restarted.DirectionKeys(){t.Fatal("reused new logical scope")}
    if err:=store.ReleaseLane("user",tunnel,1,s3.Epoch);err!=nil{t.Fatal(err)}
}


func TestR0V4ColdBundleFormatAndDefaultDenied(t *testing.T){
    if _,err:=(V4ColdSessionSnapshot{}).MarshalColdBundle();!errors.Is(err,ErrAdmissionParams) {
        t.Fatal("zero snapshot serialized as authority")
    }
    store,_:=NewV4EpochStore(2)
    tunnel:=[]byte("0123456789abcdef")
    c,s,ce,se:=v4Pair(t,store,"principal",tunnel,1,v4TestPolicy(1,CipherChaCha),[16]byte{})
    if ce!=nil||se!=nil {t.Fatalf("TLS: %v %v",ce,se)}
    snapshot,_:=c.ColdSnapshot()
    wire,err:=snapshot.MarshalColdBundle()
    if err!=nil {t.Fatal(err)}
    if string(wire[:4])!="WBCO" ||
       binary.BigEndian.Uint16(wire[4:6])!=1 ||
       binary.BigEndian.Uint16(wire[6:8])!=248 ||
       wire[8]!=0 || wire[9]!=1 || wire[10]!=CipherChaCha || wire[11]!=0 ||
       !bytes.Equal(wire[12:28],tunnel) ||
       !bytes.Equal(wire[28:44],c.Epoch[:]) ||
       !bytes.Equal(wire[44:60],c.Negotiated.IncarnationNonce[:]) ||
       binary.BigEndian.Uint16(wire[60:62])!=1400 ||
       binary.BigEndian.Uint16(wire[62:64])!=1400 {
        t.Fatal("bad precise Go cold v1 schema")
    }
    hash:=sha256.Sum256([]byte("WBD-V4-COLD-PRINCIPAL\x00principal"))
    if !bytes.Equal(wire[64:96],hash[:]) {t.Fatal("principal hash mismatch")}
    key:=snapshot.DirectionKeys()
    if !bytes.Equal(wire[96:128],key.C2S.AEADKey[:]) ||
       !bytes.Equal(wire[128:140],key.C2S.IV[:]) ||
       !bytes.Equal(wire[140:172],key.C2S.HPKey[:]) ||
       !bytes.Equal(wire[172:204],key.S2C.AEADKey[:]) ||
       !bytes.Equal(wire[204:216],key.S2C.IV[:]) ||
       !bytes.Equal(wire[216:248],key.S2C.HPKey[:]) {
        t.Fatal("wrong direction key segment")
    }
    ss,_:=s.ColdSnapshot()
    serverWire,err:=ss.MarshalColdBundle()
    if err!=nil||serverWire[8]!=1 ||
       !bytes.Equal(serverWire[12:],wire[12:]) {
        t.Fatal("client/server bundle is not the same protected negotiation")
    }
    if err:=store.ReleaseLane("principal",tunnel,1,s.Epoch);err!=nil {t.Fatal(err)}
}
func TestR0V4ColdBundleEphemeralInterop(t *testing.T){
    store,_:=NewV4EpochStore(1)
    tunnel:=[]byte("0123456789abcdef")
    c,s,ce,se:=v4Pair(t,store,"interop",tunnel,1,v4TestPolicy(1,CipherChaCha),[16]byte{})
    if ce!=nil||se!=nil {t.Fatalf("actual TLS failed: %v %v",ce,se)}
    snapshot,e:=c.ColdSnapshot()
    if e!=nil{t.Fatal(e)}
    bundle,e:=snapshot.MarshalColdBundle()
    if e!=nil{t.Fatal(e)}
    if path:=os.Getenv("WBD_COLD_FIXTURE");path!="" {
        // The keys are real session secrets, never stdout or uploaded
        // as an Actions artifact. Create-only ephemeral file, mode 0600.
        f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
        if err!=nil{t.Fatal(err)}
        _,writeErr:=f.Write(bundle[:])
        closeErr:=f.Close()
        if writeErr!=nil||closeErr!=nil {t.Fatalf("write fixture: %v close:%v",writeErr,closeErr)}
    }
    if err:=store.ReleaseLane("interop",tunnel,1,s.Epoch);err!=nil{t.Fatal(err)}
}


// Only the server epoch reservation gets entropy; nonce creation fails after
// credentials and protected request but BEFORE protected final reply/detach.
type v4EpochOnlyReader struct { calls int }
func (r *v4EpochOnlyReader) Read(dst []byte) (int,error) {
    r.calls++
    if r.calls!=1 || len(dst)!=16 { return 0,io.ErrUnexpectedEOF }
    for i:=range dst {dst[i]=byte(i+1)}
    return len(dst),nil
}

// B01: real TLS credentials and protected V4 request alone CANNOT commit
// an epoch. Admission is acknowledged only after reply+detach. No Rust owner
// is installed or advertised by this Go-only transaction proof.
func TestR0V4AdmissionCommitOnlyAfterProtectedDetachAndRollback(t *testing.T) {
    store,err:=NewV4EpochStore(1)
    if err!=nil {t.Fatal(err)}
    tunnel:=[]byte("1234567890abcdef")
    cert:=makeServerCert(t)
    routeKey:=[]byte("0123456789abcdef0123456789abcdef")
    assoc,peer:=newAssociationPeer(t)
    defer assoc.Close()
    defer peer.Close()
    ch:=make(chan error,1)
    random:=&v4EpochOnlyReader{}
    go func() {
        _,se:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
            TLS:ServerConfig{ServerName:"target.test",RouteKey:routeKey,
                TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
            ExpectedUsername:"rollback",ExpectedPassword:"secret",
            ServerLimit:1400,Random:random,
        },V4ServerOptions{DataPlaneReady:true,Epochs:store})
        ch<-se
    }()
    _,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
        TLS:ClientConfig{ServerName:"target.test",RouteKey:routeKey,Timeout:3*time.Second},
        Username:"rollback",Password:"secret",TunnelID:bytes.Clone(tunnel),
        ClientLimit:1400,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
    },V4ClientOptions{DataPlaneReady:true})
    var se error
    select {
    case se= <-ch:
    case <-time.After(5*time.Second): t.Fatal("server did not roll back after nonce failure")
    }
    if !errors.Is(se,io.ErrUnexpectedEOF) || ce==nil || random.calls!=2 {
        t.Fatalf("nonce failure accepted or wrong stage: client=%v server=%v reads=%d",
            ce,se,random.calls)
    }
    store.mu.Lock()
    left:=len(store.entries)
    store.mu.Unlock()
    if left!=0 {t.Fatalf("pre-detach uncommitted epoch leaked: %d",left)}
    // The same authenticated principal/tunnel can now attempt a fresh real
    // TLS handshake. A rejected provisional epoch MUST NOT poison admission.
    c,s,ce,se:=v4Pair(t,store,"rollback",tunnel,1,
        v4TestPolicy(1,CipherChaCha),[16]byte{})
    if ce!=nil || se!=nil {t.Fatalf("retry after rollback failed: %v %v",ce,se)}
    snap,err:=s.ColdSnapshot()
    if err!=nil {t.Fatal(err)}
    clientSnap,err:=c.ColdSnapshot()
    if err!=nil || snap.Epoch()!=clientSnap.Epoch() ||
        snap.DirectionKeys()!=clientSnap.DirectionKeys() {
        t.Fatal("actual protected reply+detach did not commit same frozen cold scope")
    }
    store.mu.Lock()
    entry:=store.entries[v4Identity("rollback",tunnel)]
    valid:=entry!=nil && entry.active && entry.pending==0 && entry.lanes==(1<<1)
    store.mu.Unlock()
    if !valid {t.Fatal("commit not active after protected reply and detach")}
    if err:=store.ReleaseLane("rollback",tunnel,1,s.Epoch);err!=nil {t.Fatal(err)}
}


// B01/B02: a package-private bridge receives a real protected, frozen Go
// admission, and Commit can follow only the real FakeTCP Detach boundary.
// This mock proves ordering, NOT a native Rust owner or production capability.
type v4RecordingOwner struct {
    prepared,committed,aborted int
    boundary uint32
    identity [16]byte
    failPrepare,failCommit bool
}
func (b *v4RecordingOwner) prepare(s V4ColdSessionSnapshot, boundary uint32, observedPeer v4PeerTransport) (v4PreparedOwner,error) {
    b.prepared++
    b.boundary=boundary
    b.identity=s.TunnelID()
    if observedPeer.mss!=faketcp.DefaultMSS || !observedPeer.advertised ||
       observedPeer.flow.ClientPort==0 || observedPeer.flow.ServerPort==0 ||
       observedPeer.flow.ClientIP==([4]byte{}) || observedPeer.flow.ServerIP==([4]byte{}) {
        return nil,ErrAdmissionParams
    }
    if b.failPrepare {return nil,ErrAdmissionUnsupported}
    if _,err:=s.MarshalColdBundle();err!=nil {return nil,err}
    return &v4RecordingPending{b:b},nil
}
type v4RecordingPending struct {b *v4RecordingOwner; committed bool}
func (p *v4RecordingPending) commit(early []faketcp.TransitionPacket, exactTXBoundary uint32) error {
    if p.committed {return ErrAdmissionParams}
    if p.b.failCommit {return ErrAdmissionUnsupported}
    p.b.committed++;p.committed=true
    return nil
}
func (p *v4RecordingPending) abort() {
    if !p.committed {p.b.aborted++;p.committed=true}
}

func TestR0V4AssociationFlowScopeComesFromOriginalFakeTCP(t *testing.T) {
    if _,err:=v4PeerTransportFromAssociation(nil);err==nil {
        t.Fatal("nil association supplied a supposed trusted flow")
    }
    assoc,peer:=newAssociationPeer(t)
    defer assoc.Close()
    defer peer.Close()
    observed,err:=v4PeerTransportFromAssociation(assoc)
    if err!=nil || observed.flow!=assoc.Flow() ||
       observed.flow.ClientPort==0 || observed.flow.ServerPort==0 ||
       observed.flow.ClientIP==([4]byte{}) || observed.flow.ServerIP==([4]byte{}) {
        t.Fatalf("owner bridge must receive original Go association tuple: %+v %v",observed,err)
    }
    // A correctly formatted copied cold bundle does NOT mint this flow;
    // only the private protected EstablishServerV4 call site passes it on.
}

func v4PairWithPrivateBridge(t *testing.T,b v4OwnerBridge,store *V4EpochStore)(
    *V4ClientSession,*V4ServerSession,error,error) {
    return v4PairWithPrivateBridgeCipher(t,b,store,CipherChaCha)
}
func v4PairWithPrivateBridgeCipher(t *testing.T,b v4OwnerBridge,store *V4EpochStore,cipher uint8,probeOnly ...bool)(
    *V4ClientSession,*V4ServerSession,error,error) {
    t.Helper()
    f2:=len(probeOnly)==1 && probeOnly[0]
    cert:=makeServerCert(t)
    key:=[]byte("0123456789abcdef0123456789abcdef")
    assoc,peer:=newAssociationPeer(t)
    defer assoc.Close()
    defer peer.Close()
    // Optional tagged test-only bridge gets the actual association to
    // inject raw records between protected Prepare and real Detach.
    if native,ok:=b.(interface{bindTestAssociation(*faketcp.ServerAssociation)});ok {
        native.bindTestAssociation(assoc)
    }
    type result struct {s *V4ServerSession;err error}
    ch:=make(chan result,1)
    go func(){
        s,e:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
            TLS:ServerConfig{ServerName:"target.test",RouteKey:key,
                TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
            ExpectedUsername:"protected-owner",ExpectedPassword:"secret",ServerLimit:1400,
        },V4ServerOptions{DataPlaneReady:true,Epochs:store,ownerBridge:b,fec2ProbeOnly:f2})
        ch<-result{s,e}
    }()
    c,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
        TLS:ClientConfig{ServerName:"target.test",RouteKey:key,Timeout:3*time.Second},
        Username:"protected-owner",Password:"secret",TunnelID:[]byte("0123456789abcdef"),
        ClientLimit:1400,LaneID:1,Policy:v4TestPolicy(1,cipher),
    },V4ClientOptions{DataPlaneReady:true,fec2ProbeOnly:f2})
    select {
    case r:= <-ch:return c,r.s,ce,r.err
    case <-time.After(5*time.Second):t.Fatal("private bridge TLS blocked");return nil,nil,nil,nil
    }
}
func TestR0V4PrivateNativeBridgeRealProtectedOrderAndAbort(t *testing.T){
    for _,fail:=range []string{"prepare","commit","none"} {
        t.Run(fail,func(t *testing.T){
            store,_:=NewV4EpochStore(1)
            b:=&v4RecordingOwner{failPrepare:fail=="prepare",failCommit:fail=="commit"}
            c,s,ce,se:=v4PairWithPrivateBridge(t,b,store)
            store.mu.Lock()
            n:=len(store.entries)
            store.mu.Unlock()
            if b.prepared!=1 || b.identity!=[16]byte{0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,
                   0x38,0x39,0x61,0x62,0x63,0x64,0x65,0x66} {
                t.Fatalf("bridge never saw protected immutable identity: %+v",b)
            }
            if fail!="none" {
                if se==nil||b.committed!=0||n!=0 {
                    t.Fatalf("failed bridge published epoch: server=%v n=%d owner=%+v",se,n,b)
                }
                if fail=="prepare" && b.aborted!=0 {
                    t.Fatal("prepare rejection never minted an owner to abort")
                }
                if fail=="commit" && b.aborted!=1 {
                    t.Fatal("failed commit must abort the already prepared owner once")
                }
                return
            }
            if ce!=nil||se!=nil || c==nil||s==nil ||
                b.committed!=1||b.aborted!=0||n!=1 {
                t.Fatalf("protected commit absent: client=%v server=%v owner=%+v epoch=%d",ce,se,b,n)
            }
            snap,e:=s.ColdSnapshot()
            if e!=nil||snap.TunnelID()!=b.identity {t.Fatal("after-commit cold owner lost provenance")}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,s.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}

func TestR0V4RealProtectedFec2Bit2FeatureAndKDFThreeCiphers(t *testing.T) {
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256} {
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(4);if err!=nil{t.Fatal(err)}
            tunnel:=[]byte("v4-fec2-probe-01")
            client,server,ce,se:=v4PairFeatureProbe(
                t,store,"fec2user",tunnel,1,v4TestPolicy(1,cipher),[16]byte{},true,true)
            if ce!=nil||se!=nil{t.Fatalf("real TLS F2 client=%v server=%v",ce,se)}
            want:=v4RequiredFeatures|v4FeatureFEC2
            if client.negotiatedFeatures!=want||server.negotiatedFeatures!=want||
               client.verifiedCold.features!=want||server.verifiedCold.features!=want||
               client.Epoch==[16]byte{}||client.Epoch!=server.Epoch||
               client.Negotiated.Keys!=server.Negotiated.Keys||
               client.Negotiated.Keys.C2S==client.Negotiated.Keys.S2C {
                t.Fatal("credential-checked protected bit2 exporter or frozen features mismatch")
            }
            cf,err:=client.ColdSnapshot()
            if err!=nil||cf.features!=want {t.Fatalf("client frozen F2 snapshot: %v",err)}
            sf,err:=server.ColdSnapshot()
            if err!=nil||sf.features!=want {t.Fatalf("server frozen F2 snapshot: %v",err)}
            // No bit2 authority is minted by the old cold248 grammar.
            cold,err:=sf.MarshalColdBundle()
            if err!=nil || cold[11]!=0 {t.Fatalf("cold248 leaked feature authority: %v",err)}
            if err:=store.ReleaseLane("fec2user",tunnel,1,client.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}
func TestR0V4RealProtectedFec2NoDowngradeAndEpochRollback(t *testing.T) {
    for _,pair:=range [][2]bool{{true,false},{false,true}} {
        store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
        tunnel:=[]byte("v4-fec2-probe-02")
        _,_,ce,se:=v4PairFeatureProbe(t,store,"user",tunnel,1,
            v4TestPolicy(1,CipherChaCha),[16]byte{},pair[0],pair[1])
        if ce==nil || !errors.Is(se,ErrAdmissionUnsupported) {
            t.Fatalf("mismatched protected features admitted client=%v server=%v",ce,se)
        }
        c,server,ce,se:=v4PairFeatureProbe(t,store,"user",tunnel,1,
            v4TestPolicy(1,CipherChaCha),[16]byte{},true,true)
        if ce!=nil||se!=nil||c.Epoch!=server.Epoch{
            t.Fatalf("mismatch left active epoch %v %v",ce,se)
        }
        if err:=store.ReleaseLane("user",tunnel,1,c.Epoch);err!=nil{t.Fatal(err)}
    }
}
func TestR0V4Fec2ExtensionExactBitPatternRejectUnknown(t *testing.T){
    var epoch [16]byte;epoch[0]=1
    for _,features:=range []uint16{0,1,2,4,5,6,8,11,15,0x8007} {
        if _,err:=v4Encode(V4Extension{Features:features,Epoch:epoch});
           !errors.Is(err,ErrAdmissionUnsupported) {
            t.Fatalf("unknown features %04x encoded: %v",features,err)
        }
    }
    for _,features:=range []uint16{v4RequiredFeatures,v4RequiredFeatures|v4FeatureFEC2} {
        wire,err:=v4Encode(V4Extension{Features:features,Epoch:epoch})
        if err!=nil{t.Fatal(err)}
        got,err:=v4Decode(wire[:])
        if err!=nil||got.Features!=features||got.Epoch!=epoch{
            t.Fatalf("exact feature %04x failed: %v",features,err)
        }
    }
}

type v4FixedProbeExporter struct{}
func (v4FixedProbeExporter) ExportKeyingMaterial(label string,context []byte,length int)([]byte,error){
    // Deterministically emulate ONLY the exporter context binding; original
    // TLS handshake tests above use real crypto/tls and real credentials.
    if length!=32{return nil,ErrAdmissionParams}
    material:=append(append([]byte(label),0),context...)
    value:=sha256.Sum256(material)
    return value[:],nil
}
func TestR0V4Fec2RealExporterContextSeparatesBit2(t *testing.T){
    var nonce [16]byte;nonce[0]=0xc4
    var epoch [16]byte;epoch[0]=0xd5
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        result:=AdmissionResult{
            RecordVersion:V4RecordVersion,Policy:v4TestPolicy(1,cipher),
            TunnelID:[]byte("0123456789abcdef"),IncarnationNonce:nonce,
            ClientLimit:1400,ServerLimit:1400,
        }
        off,err:=v4DeriveRecordKeys(v4FixedProbeExporter{},result,
            V4Extension{Features:v4RequiredFeatures,Epoch:epoch})
        if err!=nil{t.Fatal(err)}
        on,err:=v4DeriveRecordKeys(v4FixedProbeExporter{},result,
            V4Extension{Features:v4RequiredFeatures|v4FeatureFEC2,Epoch:epoch})
        if err!=nil{t.Fatal(err)}
        if off==on || off.C2S==on.C2S || off.S2C==on.S2C ||
           on.C2S==on.S2C || off.C2S==off.S2C {
            t.Fatalf("FEC2 bit2 not cryptographically separated by original exporter cipher=%d",cipher)
        }
        // Feature transcript cannot be forged using bit2 alone.
        _,err=v4DeriveRecordKeys(v4FixedProbeExporter{},result,
            V4Extension{Features:v4FeatureFEC2,Epoch:epoch})
        if !errors.Is(err,ErrAdmissionUnsupported){t.Fatalf("partial KDF feature accepted: %v",err)}
    }
}

// M0/M4 shared Stop barrier: no network cleanup if original Rust owner Stop
// cannot be confirmed. These mocks ONLY test sequencing; real backend proof
// is TestR0V4EmbeddedTwoGenerationStopIsolation on original Rust C owner.
type v4StopSequenceProbe struct{
    result V4OwnerStopCompletion
    err error
    calls int
}
func (p *v4StopSequenceProbe) StopAndReleaseOriginalOwner()(V4OwnerStopCompletion,error){
    p.calls++
    return p.result,p.err
}
func TestR0V4StopBeforeOwnedNetworkCleanupFailClosed(t *testing.T){
    var epoch [16]byte;epoch[0]=0x5c
    complete:=V4OwnerStopCompletion{Epoch:epoch,
        OwnerAndDriversDrained:true,GenerationReleased:true}
    for _,tc:=range []struct{
        name string
        stop V4OwnerStopCompletion
        fail error
        cleanup bool
    }{
        {"completed",complete,nil,true},
        {"not_stopped",V4OwnerStopCompletion{Epoch:epoch},nil,false},
        {"no_epoch",V4OwnerStopCompletion{OwnerAndDriversDrained:true,GenerationReleased:true},nil,false},
        {"stop_failed",complete,ErrAdmissionParams,false},
    }{
        t.Run(tc.name,func(t *testing.T){
            p:=&v4StopSequenceProbe{result:tc.stop,err:tc.fail}
            cleaned:=0
            got,err:=V4StopThenCleanupNetwork(p,func()error{cleaned++;return nil})
            if p.calls!=1|| (cleaned==1)!=tc.cleanup || (err==nil)!=tc.cleanup{
                t.Fatalf("incorrect original Rust Stop->Windows native owned cleanup fence: %+v got=%+v err=%v cleaned=%d",tc,got,err,cleaned)
            }
            if tc.cleanup&&got!=complete{t.Fatalf("wrong Stop receipt %+v",got)}
        })
    }
    p:=&v4StopSequenceProbe{result:complete}
    cleaned:=0
    got,err:=V4StopThenCleanupNetwork(p,func()error{
        cleaned++
        return ErrAdmissionParams
    })
    if err==nil||got!=complete||cleaned!=1{
        t.Fatalf("cleanup failure hid partially-owned network state: receipt=%+v err=%v cleanup=%d",got,err,cleaned)
    }
    p.calls=0
    if _,err:=V4StopThenCleanupNetwork(p,nil);err==nil||p.calls!=0{
        t.Fatal("nil cleanup must reject BEFORE consuming Rust Stop")
    }
    t.Log("M0_STOP_AND_OWNED_NETWORK_CLEANUP_ORDER_FAIL_CLOSED_PASS no_fake_disconnected=1")
}
