package v4routekey

import (
 "encoding/hex"
 "strings"
 "testing"
)

func TestH2207ShortRouteKeyIndependentPBKDF2Vectors(t *testing.T) {
  for _,tc:=range []struct{input,want string}{
    {"Abc12345","9cafa60c5da912db6a526c4e211ed402052a1684edee82bab8aea14a8be54e0d"},
    {"A1b2C3d4E5f6G7h8","72043e311dfcfa69188bebe3b1ffde70c5b548c43c5abdaeadaf31c788f20646"},
    {"ABCdef0123456789ABCdef0123456789","063e483cfd4433157aec7d1d6cb062f22317c4122b66131c8aef5d5aaa88159c"},
  } {
    key,err:=Derive(tc.input)
    if err!=nil||len(key)!=32||hex.EncodeToString(key)!=tc.want {
      t.Fatalf("offline SHA256 PBKDF2 vector mismatch length=%d err=%v",len(key),err)
    }
    again,_:=Derive(tc.input)
    if !strings.EqualFold(hex.EncodeToString(again),tc.want){
      t.Fatalf("same client/server input diverges")
    }
  }
}
func TestH2207ShortRouteKeyRejectsAmbiguousOrLowLength(t *testing.T) {
 for _,input:=range []string{
  "", "1234567", strings.Repeat("x",33), "ABC 12345", "ABC-12345",
  "ABC_12345","ABC\n12345","abcdefgh\x00","中文密钥A1", "ＡＢＣ１２３４５",
 } {
   key,err:=Derive(input)
   if err==nil||key!=nil{t.Fatalf("accepted invalid 8..32 ASCII route-key (length=%d)",len(input))}
 }
 a,_:=Derive("Abc12345")
 b,_:=Derive("abc12345")
 if hex.EncodeToString(a)==hex.EncodeToString(b){t.Fatal("short key lost case-sensitivity")}
}
