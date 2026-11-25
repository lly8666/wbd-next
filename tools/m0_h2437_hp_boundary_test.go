package tlsrecord
import ("encoding/binary";"encoding/hex";"testing")
func TestH2437TerminalHeaderMask(t *testing.T){
 var key [32]byte;for i:=range key{key[i]=byte(i)}
 for _,v:=range []struct{c uint32;want string}{{0,"103af111c18b549d"},{1,"89fb08002917a540"},{0xfffffffe,"76e88a6c6c8e86c7"},{0xffffffff,"14eed149cd60a456"}}{
  var sample [16]byte;binary.LittleEndian.PutUint32(sample[:4],v.c);for i:=0;i<12;i++{sample[4+i]=byte(i)}
  got,err:=headerMask(key,sample[:]);if err!=nil||hex.EncodeToString(got[:])!=v.want{t.Fatalf("counter %x mask %x err %v",v.c,got,err)}
 }
}
