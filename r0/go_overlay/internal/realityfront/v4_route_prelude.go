package realityfront

import (
 "bytes"
 "context"
 "crypto/ecdh"
 "crypto/rand"
 "crypto/sha256"
 "errors"
 "io"
 "net"
 "time"

 "golang.org/x/crypto/hkdf"
)

// This 2x37-byte COLD FakeTCP bootstrap prelude finishes BEFORE the FIRST
// recognized WBD TLS ClientHello. X25519 shares are fresh for each original
// lane/session. No secret/password/static route token is user-provisioned,
// serialized into TLS, or added to the Rust record/data-plane wire.
// The classifier still authenticates its ClientHello marker; the real TLS
// certificate and protected username/password must authenticate independently.
const v4AutoRoutePreludeMagic = "WB-R1"

var errV4AutoRoutePrelude=errors.New("realityfront: invalid automatic pre-ClientHello route exchange")

func v4AutoRouteKDF(secret,serverPub,clientPub []byte)([]byte,error){
 if len(secret)!=32||len(serverPub)!=32||len(clientPub)!=32{return nil,errV4AutoRoutePrelude}
 hash:=sha256.New()
 _,_=hash.Write([]byte("WBD-V4-ROUTE-AUTO-X25519-TRANSCRIPT-v1"))
 _,_=hash.Write(serverPub)
 _,_=hash.Write(clientPub)
 salt:=hash.Sum(nil)
 key:=make([]byte,32)
 if _,err:=io.ReadFull(hkdf.New(sha256.New,secret,salt,
  []byte("WBD V4 first recognized TLS ClientHello marker key v1")),key);err!=nil{return nil,err}
 return key,nil
}
func v4AutoRoutePrelude(ctx context.Context,conn net.Conn,server bool,limit time.Duration)([]byte,error){
 if ctx==nil||conn==nil||limit<=0||ctx.Err()!=nil{return nil,errV4AutoRoutePrelude}
 if err:=conn.SetDeadline(time.Now().Add(limit));err!=nil{return nil,err}
 curve:=ecdh.X25519()
 var local,remote [len(v4AutoRoutePreludeMagic)+32]byte
 var private *ecdh.PrivateKey
 var err error
 if server{
  private,err=curve.GenerateKey(rand.Reader)
  if err!=nil{return nil,err}
  copy(local[:],v4AutoRoutePreludeMagic)
  copy(local[len(v4AutoRoutePreludeMagic):],private.PublicKey().Bytes())
  if err=writeFull(conn,local[:]);err!=nil{return nil,err}
  if _,err=io.ReadFull(conn,remote[:]);err!=nil{return nil,err}
 }else{
  if _,err=io.ReadFull(conn,remote[:]);err!=nil{return nil,err}
  private,err=curve.GenerateKey(rand.Reader)
  if err!=nil{return nil,err}
  copy(local[:],v4AutoRoutePreludeMagic)
  copy(local[len(v4AutoRoutePreludeMagic):],private.PublicKey().Bytes())
  if err=writeFull(conn,local[:]);err!=nil{return nil,err}
 }
 if !bytes.Equal(remote[:len(v4AutoRoutePreludeMagic)],[]byte(v4AutoRoutePreludeMagic)){
  return nil,errV4AutoRoutePrelude
 }
 public,err:=curve.NewPublicKey(remote[len(v4AutoRoutePreludeMagic):])
 if err!=nil{return nil,errV4AutoRoutePrelude}
 secret,err:=private.ECDH(public)
 if err!=nil{return nil,errV4AutoRoutePrelude}
 if server{return v4AutoRouteKDF(secret,local[len(v4AutoRoutePreludeMagic):],remote[len(v4AutoRoutePreludeMagic):])}
 return v4AutoRouteKDF(secret,remote[len(v4AutoRoutePreludeMagic):],local[len(v4AutoRoutePreludeMagic):])
}
