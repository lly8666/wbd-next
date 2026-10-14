// R0 pinned-legacy compile probe; copied into internal/realityfront ONLY inside
// the exact legacy SOURCE checkout in GitHub Actions. Not production admission.
// It deliberately calls unexported ORIGINAL Go V3 writers/readers.
package realityfront

import (
    "bytes"
    "crypto/sha256"
    "encoding/binary"
    "encoding/hex"
    "errors"
    "fmt"
    "io"
    "testing"

    "golang.org/x/crypto/hkdf"
    "github.com/lly8666/wobuzhidao/internal/tlsrecord"
)

const (
    r0V4Version uint16 = 4
    r0V4ExtensionSize = 24
    r0V4FeatureMask uint16 = 0x0003
)

// Exact, manually specified offsets (no struct/network dumping):
// schema BE16; features BE16; logical epoch [16]; feedback_page_limit; reserved [3].
func r0Extension(epoch [16]byte, features uint16) [r0V4ExtensionSize]byte {
    var ext [r0V4ExtensionSize]byte
    binary.BigEndian.PutUint16(ext[0:2], 1)
    binary.BigEndian.PutUint16(ext[2:4], features)
    copy(ext[4:20], epoch[:])
    ext[20] = 8
    return ext
}

func r0ReadExtension(raw []byte, wantEpochZero bool) ([16]byte, error) {
    var epoch [16]byte
    if len(raw) != r0V4ExtensionSize ||
       binary.BigEndian.Uint16(raw[0:2]) != 1 ||
       binary.BigEndian.Uint16(raw[2:4]) != r0V4FeatureMask ||
       raw[20] != 8 || raw[21] != 0 || raw[22] != 0 || raw[23] != 0 {
        return epoch, ErrAdmissionParams
    }
    copy(epoch[:], raw[4:20])
    zero := epoch == [16]byte{}
    if zero != wantEpochZero { return [16]byte{}, ErrAdmissionParams }
    return epoch, nil
}

func r0Policy(cipher uint8) AdmissionPolicy {
    return AdmissionPolicy{
        Schema: PolicySchemaV3, Transport: TransportNormal,
        DesiredLanes: 1, FECMode: FECFixed, FixedParity: 4,
        Cipher: cipher,
    }
}

func r0Request(cipher uint8) AdmissionRequest {
    return AdmissionRequest{
        RecordVersion: RecordVersionV3, LaneID: 1,
        TunnelID: []byte("0123456789abcdef"), ClientLimit: 1400,
        Username: "u", Password: "p", Policy: r0Policy(cipher),
    }
}

func r0Reply(cipher uint8) AdmissionResult {
    var nonce [16]byte
    for i := range nonce { nonce[i] = byte(i) }
    return AdmissionResult{
        RecordVersion: RecordVersionV3, LaneID: 1,
        TunnelID: []byte("0123456789abcdef"),
        ClientLimit: 1400, ServerLimit: 1350,
        IncarnationNonce: nonce, Policy: r0Policy(cipher),
    }
}

func r0Hex(t *testing.T, got []byte, expected string) {
    t.Helper()
    if hex.EncodeToString(got) != expected {
        t.Fatalf("golden mismatch\n got=%x\nwant=%s", got, expected)
    }
}

const r0TunnelHex = "30313233343536373839616263646566"
const r0PolicyHex = "01010101040000000100"
const r0V3ReqHex = "574241440003057801001000010001" + r0TunnelHex + "7570" + r0PolicyHex
const r0V3ReplyHex = "000003000102030405060708090a0b0c0d0e0f05780546010010" + r0TunnelHex + r0PolicyHex
const r0V4ExtRequestHex = "00010003" + "00000000000000000000000000000000" + "08000000"
const r0V4ExtReplyHex = "00010003" + "a0a1a2a3a4a5a6a7a8a9aaabacadaeaf" + "08000000"

func r0V4Request(t *testing.T) []byte {
    t.Helper()
    v3, err := marshalAdmissionRequest(r0Request(CipherChaCha))
    if err != nil { t.Fatal(err) }
    v4 := bytes.Clone(v3)
    binary.BigEndian.PutUint16(v4[4:6], r0V4Version)
    ext := r0Extension([16]byte{}, r0V4FeatureMask)
    return append(v4, ext[:]...)
}

func r0V4Reply(t *testing.T) []byte {
    t.Helper()
    v3, err := marshalAdmissionReply(r0Reply(CipherChaCha))
    if err != nil { t.Fatal(err) }
    v4 := bytes.Clone(v3)
    binary.BigEndian.PutUint16(v4[1:3], r0V4Version)
    var assigned [16]byte
    for i := range assigned { assigned[i] = byte(0xa0 + i) }
    ext := r0Extension(assigned, r0V4FeatureMask)
    return append(v4, ext[:]...)
}

func r0ReadV4Request(wire []byte) (AdmissionRequest, [16]byte, error) {
    var zero [16]byte
    if len(wire) < admissionRequestLen+r0V4ExtensionSize ||
       binary.BigEndian.Uint16(wire[4:6]) != r0V4Version {
        return AdmissionRequest{}, zero, ErrAdmissionVersion
    }
    base := bytes.Clone(wire[:len(wire)-r0V4ExtensionSize])
    binary.BigEndian.PutUint16(base[4:6], RecordVersionV3)
    request, err := readAdmissionRequest(bytes.NewReader(base))
    if err != nil { return AdmissionRequest{}, zero, err }
    expected := admissionRequestLen+len(request.TunnelID)+len(request.Username)+len(request.Password)+policyV3Len
    if request.AutoLease { expected += 17 }
    if len(base) != expected { return AdmissionRequest{}, zero, ErrAdmissionParams }
    if err := request.Policy.SupportedNow(); err != nil { return AdmissionRequest{}, zero, err }
    epoch, err := r0ReadExtension(wire[len(base):], true)
    if err != nil { return AdmissionRequest{}, zero, err }
    return request, epoch, nil
}

func r0ReadV4Reply(wire []byte, request AdmissionRequest) (AdmissionResult, [16]byte, error) {
    var zero [16]byte
    if len(wire) < admissionReplyLen+r0V4ExtensionSize ||
       binary.BigEndian.Uint16(wire[1:3]) != r0V4Version {
        return AdmissionResult{}, zero, ErrAdmissionVersion
    }
    base := bytes.Clone(wire[:len(wire)-r0V4ExtensionSize])
    binary.BigEndian.PutUint16(base[1:3], RecordVersionV3)
    result, err := readAdmissionReply(bytes.NewReader(base), request)
    if err != nil { return AdmissionResult{}, zero, err }
    expected := admissionReplyLen+len(result.TunnelID)+policyV3Len
    if request.AutoLease { expected += 4 }
    if len(base) != expected { return AdmissionResult{}, zero, ErrAdmissionParams }
    epoch, err := r0ReadExtension(wire[len(base):], false)
    if err != nil { return AdmissionResult{}, zero, err }
    return result, epoch, nil
}

func TestR0PinnedGoV3RequestReplyGolden(t *testing.T) {
    request, err := marshalAdmissionRequest(r0Request(CipherChaCha))
    if err != nil { t.Fatal(err) }
    r0Hex(t, request, r0V3ReqHex)
    parsed, err := readAdmissionRequest(bytes.NewReader(request))
    if err != nil || parsed.Policy != r0Policy(CipherChaCha) {
        t.Fatalf("original V3 request decode: %+v %v", parsed.Policy, err)
    }
    reply, err := marshalAdmissionReply(r0Reply(CipherChaCha))
    if err != nil { t.Fatal(err) }
    r0Hex(t, reply, r0V3ReplyHex)
    result, err := readAdmissionReply(bytes.NewReader(reply), r0Request(CipherChaCha))
    if err != nil || result.Policy != r0Policy(CipherChaCha) {
        t.Fatalf("original V3 reply decode: %+v %v", result.Policy, err)
    }
    t.Logf("R0 V3 original Go request=%x reply=%x", request, reply)
}

func TestR0V4Admission24ByteExtensionGolden(t *testing.T) {
    request := r0V4Request(t)
    reply := r0V4Reply(t)
    r0Hex(t, request, "574241440004057801001000010001"+r0TunnelHex+"7570"+r0PolicyHex+r0V4ExtRequestHex)
    r0Hex(t, reply, "000004000102030405060708090a0b0c0d0e0f05780546010010"+r0TunnelHex+r0PolicyHex+r0V4ExtReplyHex)
    r, requestEpoch, err := r0ReadV4Request(request)
    if err != nil || requestEpoch != [16]byte{} || r.Policy != r0Policy(CipherChaCha) {
        t.Fatalf("V4 request envelope rejected: %+v %x %v", r.Policy, requestEpoch, err)
    }
    answer, assignedEpoch, err := r0ReadV4Reply(reply, r)
    if err != nil || assignedEpoch == [16]byte{} || answer.Policy != r.Policy {
        t.Fatalf("V4 reply envelope rejected: %+v %x %v", answer.Policy, assignedEpoch, err)
    }
    if _, err = readAdmissionRequest(bytes.NewReader(request)); !errors.Is(err, ErrAdmissionVersion) {
        t.Fatalf("old V3 parser silently accepted V4: %v", err)
    }
    if _, err = readAdmissionReply(bytes.NewReader(reply), r); !errors.Is(err, ErrAdmissionParams) {
        t.Fatalf("old V3 reply parser silently accepted V4: %v", err)
    }
    t.Logf("R0 V4 proposed bytes request=%x reply=%x", request, reply)
}

func TestR0V4RejectMalformedAndDowngrade(t *testing.T) {
    req := r0V4Request(t)
    reply := r0V4Reply(t)
    for _, test := range []struct {
        name string; offset int; value byte
    }{
        {"schema", len(req)-24, 2},
        {"unknown-feature", len(req)-21, 0x80},
        {"required-feature-missing", len(req)-21, 1},
        {"page-limit", len(req)-4, 7},
        {"reserved", len(req)-1, 1},
        {"request-epoch-reuse", len(req)-20, 9},
        {"policy-bad-cipher", len(req)-24-2, 9},
    } {
        t.Run(test.name,func(t *testing.T){
            corrupted := bytes.Clone(req)
            corrupted[test.offset] = test.value
            if _, _, err := r0ReadV4Request(corrupted); err == nil {
                t.Fatalf("accepted malformed %s", test.name)
            }
        })
    }
    for cut := 1; cut <= 24; cut++ {
        if _, _, err := r0ReadV4Request(req[:len(req)-cut]); err == nil {
            t.Fatalf("request truncated by %d accepted", cut)
        }
        if _, _, err := r0ReadV4Reply(reply[:len(reply)-cut],r0Request(CipherChaCha)); err == nil {
            t.Fatalf("reply truncated by %d accepted", cut)
        }
    }
    bad := bytes.Clone(reply)
    bad[len(reply)-20] = 0 // assigned epoch first byte may be 0, so set all zero instead
    copy(bad[len(reply)-20:len(reply)-4], make([]byte,16))
    if _,_,err := r0ReadV4Reply(bad,r0Request(CipherChaCha));err==nil {
        t.Fatal("zero server epoch accepted")
    }
    wrong := bytes.Clone(reply)
    wrong[len(reply)-21]=1
    if _,_,err := r0ReadV4Reply(wrong,r0Request(CipherChaCha));err==nil {
        t.Fatal("reply feature mismatch accepted")
    }
}

func r0V4ExporterHash(result AdmissionResult, replyExtension []byte) ([32]byte,error) {
    if len(replyExtension)!=24 { return [32]byte{}, fmt.Errorf("not V4 extension") }
    if _,err:=r0ReadExtension(replyExtension,false);err!=nil{return [32]byte{},err}
    policy,err:=result.Policy.Encode()
    if err!=nil{return [32]byte{},err}
    if len(result.TunnelID)>0xffff{return [32]byte{},ErrAdmissionParams}
    raw := make([]byte,0,2+16+2+len(result.TunnelID)+2+2+10+24)
    var v [2]byte
    binary.BigEndian.PutUint16(v[:], r0V4Version); raw=append(raw,v[:]...)
    raw=append(raw,result.IncarnationNonce[:]...)
    binary.BigEndian.PutUint16(v[:],uint16(len(result.TunnelID)));raw=append(raw,v[:]...)
    raw=append(raw,result.TunnelID...)
    binary.BigEndian.PutUint16(v[:],result.ClientLimit);raw=append(raw,v[:]...)
    binary.BigEndian.PutUint16(v[:],result.ServerLimit);raw=append(raw,v[:]...)
    raw=append(raw,policy[:]...)
    raw=append(raw,replyExtension...)
    return sha256.Sum256(raw),nil
}

func r0V4HKDF(master []byte, nonce [16]byte, suite, direction string) ([76]byte,error) {
    var result [76]byte
    if len(master)!=32{return result,ErrAdmissionParams}
    if direction!="c2s"&&direction!="s2c"{return result,ErrAdmissionParams}
    if suite!="chacha20-poly1305"&&suite!="aes-128-gcm"&&suite!="aes-256-gcm" {
        return result,ErrAdmissionParams
    }
    info := []byte("WBD-TLSLIKE-V4/"+suite+"/"+direction)
    _,err:=io.ReadFull(hkdf.New(sha256.New,master,nonce[:],info),result[:])
    return result,err
}

func TestR0GoV4ExporterAndHKDFDomainSeparation(t *testing.T) {
    reply := r0V4Reply(t)
    result := r0Reply(CipherChaCha)
    fingerprint,err:=r0V4ExporterHash(result,reply[len(reply)-24:])
    if err!=nil { t.Fatal(err) }
    policy,err:=result.Policy.Encode();if err!=nil{t.Fatal(err)}
    v3hash,err:=tlsrecord.ExporterContextHashV3(3,result.IncarnationNonce,result.TunnelID,result.ClientLimit,result.ServerLimit,policy[:])
    if err!=nil || fingerprint==v3hash {t.Fatal("V4 exporter not domain separated from V3")}
    master:=make([]byte,32)
    for i:=range master {master[i]=byte(i)}
    suites:=[]struct{name string;id uint8}{{"chacha20-poly1305",1},{"aes-128-gcm",2},{"aes-256-gcm",3}}
    // Observed in the first pinned-Go Actions run (38509549705) and now
    // frozen as regression goldens. A SHA check guards drift but does not,
    // by itself, independently prove the V4 design is correct.
    expected := map[string][2]string{
        "chacha20-poly1305": {"ab52003578ce47f32c6ca03ac8223bc5077dbb03daac022a36c21f66f6db2253", "5835468c258178f6faa80fd0c66445a4aa7dcc913cc34b00ea971f055896ca01"},
        "aes-128-gcm": {"ef06ef058a13dac1738a5194af35f6b7171b1f092b76b78b6ebe0ea9546d053f", "5ccde5e9dcdc9de4278d492462f294ee248ccb860c8bc3159d8b474dffab6dd9"},
        "aes-256-gcm": {"c04520a8c61bd91bafb84efde2e7ba2abb9773102e0fed3d3e1dc4b34917d753", "1a946f21a125f7bc48ceb6cf39f8bee6b6387013c04746f37ae451dd21a5653b"},
    }
    keys:=map[string][76]byte{}
    for _,s:=range suites {
        c2s,err:=r0V4HKDF(master,result.IncarnationNonce,s.name,"c2s")
        if err!=nil {t.Fatal(err)}
        s2c,err:=r0V4HKDF(master,result.IncarnationNonce,s.name,"s2c")
        if err!=nil||c2s==s2c{t.Fatalf("V4 direction separation %s: %v",s.name,err)}
        for _,other:=range keys {if c2s==other||s2c==other{t.Fatal("cross-suite/direction collision")}}
        keys[s.name+"/c2s"]=c2s
        keys[s.name+"/s2c"]=s2c
        old,err:=tlsrecord.DeriveKeysV3(master,result.IncarnationNonce,s.id)
        if err!=nil || bytes.Equal(c2s[:],old.C2S.AEADKey[:]) {
            t.Fatalf("V3/V4 KDF shared material for suite %s: %v",s.name,err)
        }
        if fmt.Sprintf("%x",sha256.Sum256(c2s[:])) != expected[s.name][0] ||
           fmt.Sprintf("%x",sha256.Sum256(s2c[:])) != expected[s.name][1] {
            t.Fatalf("V4 HKDF golden drift for %s",s.name)
        }
        t.Logf("R0 V4 %s c2s-sha256=%x s2c-sha256=%x",s.name,sha256.Sum256(c2s[:]),sha256.Sum256(s2c[:]))
    }
    if fmt.Sprintf("%x",fingerprint) != "8f6e83e2e9d20452ffb40ed6461225373dd849a50f20fc6f25571aa5e42c51cd" ||
       fmt.Sprintf("%x",v3hash) != "25a0a67859e75aaeb9ecce39cf455d475e934a59e61c566d0246cfb63a9046b0" {
        t.Fatal("exporter context golden drift")
    }
    t.Logf("R0 V4 exporter context=%x V3 context=%x",fingerprint,v3hash)
}

func TestR0OriginalGoCipherPolicyIsExplicit(t *testing.T) {
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256} {
        req:=r0Request(cipher)
        original,err:=marshalAdmissionRequest(req)
        if err!=nil{t.Fatalf("V3 %d writer: %v",cipher,err)}
        decoded,err:=readAdmissionRequest(bytes.NewReader(original))
        if err!=nil||decoded.Policy.Cipher!=cipher{t.Fatalf("V3 cipher %d not bound: %v",cipher,err)}
    }
}
