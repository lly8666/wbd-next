package faketcp
import ("encoding/binary";"testing";"time")
func TestV4PublicSYNAndSYNACKRealEncodedOptionsAndFrozenRetries(t *testing.T){
 defer func(){_=SetPublicV4AdvertisedMSS(DefaultMSS)}()
 flow:=ClientFlow{LocalIP:[4]byte{10,66,0,2},PeerIP:[4]byte{10,66,0,1},LocalPort:22001,PeerPort:443}
 for _,v:=range []struct{outer,mss uint16}{{1400,1360},{1460,1420},{1500,1460}}{
  if err:=SetPublicV4AdvertisedMSS(v.mss);err!=nil{t.Fatal(err)}
  var sent []Segment
  client,err:=NewClientAssociation(flow,1000,time.Second,func(seg Segment)error{sent=append(sent,seg);return nil})
  if err!=nil{t.Fatal(err)}
  now:=time.Now()
  if err=client.Start(now);err!=nil{t.Fatal(err)}
  if len(sent)!=1||sent[0].MSS!=v.mss{t.Fatalf("SYN outer=%d: %+v",v.outer,sent)}
  encoded:=MarshalSegment(sent[0],1,PacketPersonaWindows11)
  if got:=binary.BigEndian.Uint16(encoded[42:44]);got!=v.mss{t.Fatalf("actual SYN option MSS %d want %d",got,v.mss)}
  parsed,err:=ParseIPv4TCP(encoded)
  if err!=nil||parsed.MSS!=v.mss||!IsWBDHandshakeSegment(parsed){t.Fatalf("parsed SYN %+v error=%v",parsed,err)}
  if _,err=client.EmitRetransmitDue(now.Add(3*time.Second));err!=nil{t.Fatal(err)}
  _=SetPublicV4AdvertisedMSS(1460)
  if len(sent)<2||sent[len(sent)-1].MSS!=v.mss{t.Fatalf("SYN retry changed: %+v",sent)}
  _=SetPublicV4AdvertisedMSS(v.mss)
  server,err:=NewServerAssociation(parsed,9000,time.Second,nil)
  if err!=nil{t.Fatal(err)}
  ack,err:=server.SYNACKSegment()
  if err!=nil||ack.MSS!=v.mss{t.Fatalf("SYNACK %d err=%v",ack.MSS,err)}
  encoded=MarshalSegment(ack,2,PacketPersonaWindows11)
  if got:=binary.BigEndian.Uint16(encoded[42:44]);got!=v.mss{t.Fatalf("actual SYNACK option %d want %d",got,v.mss)}
  _=SetPublicV4AdvertisedMSS(1360)
  retry,err:=server.SYNACKSegment()
  if err!=nil||retry.MSS!=v.mss{t.Fatalf("frozen SYNACK changed %d error=%v",retry.MSS,err)}
  client.Close();server.Close()
 }
}
func TestV4LocalMSSRejectsInvalid(t *testing.T){
 for _,bad:=range []uint16{0,535,1461,65535}{
  if SetPublicV4AdvertisedMSS(bad)==nil{t.Fatalf("accepted invalid MSS %d",bad)}
 }
}
