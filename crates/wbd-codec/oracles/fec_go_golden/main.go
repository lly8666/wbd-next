// Native Go 1.23 reference reproducing pinned wobuzhidao@a7a82db3
// internal/fec/fec.go gf{Mul,Inv,Pow}, buildGenerator and
// internal/fec/fastblock_encoder.go min(activeK,configuredParity).
// GO RUN: go run crates/wbd-codec/oracles/fec_go_golden/main.go
// This is a standalone source-level reproduction, NOT a claim that the
// original old-Go package ran in M3 GitHub Actions.
package main

import (
 "crypto/sha256"
 "fmt"
)

func mul(a,b byte)byte {
 var r byte
 for b>0 {
  if b&1>0 {r^=a}
  hi:=a&0x80;a<<=1
  if hi>0 {a^=0x1d} // 0x11d reduction after removing implicit bit 8
  b>>=1
 }
 return r
}
func pow(a byte,n int)byte{
 var r byte=1
 for n>0 {if n&1>0{r=mul(r,a)};a=mul(a,a);n>>=1}
 return r
}
func inv(a byte)byte{if a==0{panic("inverse of zero")};return pow(a,254)}
func generator()[40][20]byte{
 var v[40][20]byte
 for r:=0;r<40;r++{for c:=0;c<20;c++{v[r][c]=pow(byte(r+1),c)}}
 var aug[20][40]byte
 for r:=0;r<20;r++{copy(aug[r][:20],v[r][:]);aug[r][20+r]=1}
 for col:=0;col<20;col++{
  pivot:=col;for pivot<20&&aug[pivot][col]==0{pivot++}
  if pivot==20{panic("singular")}
  aug[col],aug[pivot]=aug[pivot],aug[col]
  scale:=inv(aug[col][col])
  for c:=0;c<40;c++{aug[col][c]=mul(aug[col][c],scale)}
  for r:=0;r<20;r++{
   if r==col{continue}
   factor:=aug[r][col]
   for c:=0;c<40;c++{aug[r][c]^=mul(factor,aug[col][c])}
  }
 }
 var g[40][20]byte
 for r:=0;r<40;r++{for c:=0;c<20;c++{
  for i:=0;i<20;i++{g[r][c]^=mul(v[r][i],aug[i][20+c])}
 }}
 return g
}
func encode(g[40][20]byte,src[][]byte,profile int)[][]byte{
 sent:=len(src);if sent>profile{sent=profile}
 length:=0;for _,s:=range src{if len(s)>length{length=len(s)}}
 out:=make([][]byte,sent)
 for p:=0;p<sent;p++{
  out[p]=make([]byte,length)
  for i,s:=range src{for j,b:=range s{out[p][j]^=mul(g[20+p][i],b)}}
 }
 return out
}
func main(){
 g:=generator()
 var matrix []byte
 for i:=range g{matrix=append(matrix,g[i][:]...)}
 fmt.Printf("G_SHA256=%x\n",sha256.Sum256(matrix))
 fmt.Printf("G_ROW20=%x\nG_ROW39=%x\n",g[20],g[39])
 partial:=[][]byte{{1,2,3},{0xa0,0xb1,0xc2,0xd3,0xe4}}
 for p,b:=range encode(g,partial,4){fmt.Printf("k2_R4_SENT_P%d=%x\n",p,b)}
 full:=make([][]byte,20)
 for i:=range full{
  full[i]=make([]byte,17)
  for j:=range full[i]{full[i][j]=byte(i*13+j*7+5)}
 }
 parity:=encode(g,full,20)
 var all []byte
 for _,p:=range parity{all=append(all,p...)}
 fmt.Printf("k20_L17_PARITY_SHA256=%x\n",sha256.Sum256(all))
 fmt.Printf("k20_L17_P0=%x\nk20_L17_P19=%x\n",parity[0],parity[19])
}
