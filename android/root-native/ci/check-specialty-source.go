//go:build ignore

// Fast CI-only source admission, before Rust builds. The full same-source
// Android Go compiler/linker remains authoritative for types and ABI.
package main

import (
 "fmt"
 "go/ast"
 "go/parser"
 "go/token"
 "os"
)

func main() {
 args:=os.Args[1:]
 if len(args)>0&&args[0]=="--"{args=args[1:]}
 if len(args)==0{fmt.Fprintln(os.Stderr,"no specialty sources");os.Exit(2)}
 fset:=token.NewFileSet()
 failed:=false
 for _,path:=range args{
  f,e:=parser.ParseFile(fset,path,nil,parser.AllErrors)
  if e!=nil{fmt.Fprintln(os.Stderr,e);failed=true;continue}
  // These two small fixtures use no goto or labels. A bare label was
  // accidentally introduced in B95 instead of a short declaration.
  // Do not let that typo consume a complete native build again.
  ast.Inspect(f,func(n ast.Node)bool{
   if l,ok:=n.(*ast.LabeledStmt);ok{
    fmt.Fprintf(os.Stderr,"%s: unexpected CI fixture label %q; check := declaration\n",fset.Position(l.Pos()),l.Label.Name)
    failed=true
   }
   return true
  })
 }
 if failed{os.Exit(1)}
 fmt.Println("B96_SPECIALTY_SOURCE_ADMISSION_PASS")
}
