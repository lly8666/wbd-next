package realityfront

import (
 "bytes"
 "context"
 "net"
 "testing"
 "time"
)
func TestPLAN028AutoRoutePreludeBeforeClientHelloPerLane(t *testing.T){
 var prior []byte
 for lane:=0;lane<4;lane++{
  a,b:=net.Pipe()
  serverResult:=make(chan []byte,1)
  errResult:=make(chan error,1)
  go func(){
   key,err:=v4AutoRoutePrelude(context.Background(),a,true,2*time.Second)
   serverResult<-key
   errResult<-err
   a.Close()
  }()
  client,err:=v4AutoRoutePrelude(context.Background(),b,false,2*time.Second)
  if err!=nil{t.Fatal(err)}
  b.Close()
  server:=<-serverResult
  if err:=<-errResult;err!=nil{t.Fatal(err)}
  if len(client)!=32||!bytes.Equal(client,server){t.Fatal("independently derived client/server marker key differs")}
  if lane>0&&bytes.Equal(prior,client){t.Fatal("a shared static route token was reused across Game lanes")}
  prior=client
 }
}
func TestPLAN028AutoRoutePreludeRefusesCorruptAndMissingPeer(t *testing.T){
 if _,err:=v4AutoRoutePrelude(context.Background(),nil,false,time.Second);err==nil{t.Fatal("nil peer accepted")}
 a,b:=net.Pipe()
 go func(){defer a.Close();_,_=a.Write(bytes.Repeat([]byte{0x42},37))}()
 if _,err:=v4AutoRoutePrelude(context.Background(),b,false,time.Second);err==nil{t.Fatal("invalid bootstrap marker accepted")}
 b.Close()
}
