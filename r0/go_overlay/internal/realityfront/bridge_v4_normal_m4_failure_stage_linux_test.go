//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

import (
    "errors"
    "fmt"
    "strings"
    "testing"
)

// A genuine server Normal admission can reject after the protected TLS
// reply and client local Ready. This verifies that the native refusal is
// identifiable at its precise M4 boundary, without ever logging untrusted
// error text or losing errors.Is/As and an original numeric Rust status.
func TestPLAN028NormalM4StageErrorPreservesEvidenceAndSecrets(t *testing.T){
    status:=&v4EmbeddedNativeStatus{Operation:"rust_loop_start",Code:7}
    cause:=fmt.Errorf("%w: Rust original owner loop=%d",status,status.Code)
    wrapped:=errors.Join(normalM4Fail("rust_loop_start",cause),
        errors.New("cleanup completed"))
    if V4NormalM4FailureStage(wrapped)!="rust_loop_start"{
        t.Fatalf("lost native M4 failure stage: %q",V4NormalM4FailureStage(wrapped))
    }
    if V4NormalM4NativeCode(wrapped)!=7{
        t.Fatalf("lost native RC: %d",V4NormalM4NativeCode(wrapped))
    }
    if !errors.Is(wrapped,errV4Embedded){t.Fatal("lost original fail-closed error")}
    if strings.Contains(wrapped.Error(),"user-secret")||
        strings.Contains(wrapped.Error(),"internal account"){
        t.Fatal("unsafe rejection diagnostic")
    }
    if V4NormalM4FailureStage(errors.New("unknown"))!="unclassified"||
        V4NormalM4NativeCode(errors.New("unknown"))!=-1{
        t.Fatal("untyped failure must stay explicit unknown, never pretend native RC=0")
    }
}
