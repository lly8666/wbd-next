// Package v4routekey derives the unchanged 32-byte WBD TLS route-recognition
// HMAC key from a user-entered 8..32 ASCII alphanumeric secret. No new wire
// format or TLS prelude is introduced: both peers derive locally before Hello.
// A short human-chosen password has LOW entropy regardless of KDF output size.
// Prefer 24..32 cryptographically random alphanumeric characters in production.
package v4routekey

import (
    "crypto/sha256"
    "errors"
    "golang.org/x/crypto/pbkdf2"
)

const Iterations = 240000
const MinLength = 8
const MaxLength = 32
const domainSalt = "WBD-V4-ROUTE-KEY-PBKDF2-SHA256-v1\x00"

var ErrShortRouteKey = errors.New("route-key requires 8..32 ASCII letters/digits, case-sensitive")

func Derive(passphrase string) ([]byte,error) {
    if len(passphrase)<MinLength||len(passphrase)>MaxLength {
        return nil,ErrShortRouteKey
    }
    for i:=0;i<len(passphrase);i++{
        ch:=passphrase[i]
        if !(ch>='0'&&ch<='9'||ch>='A'&&ch<='Z'||ch>='a'&&ch<='z'){
            return nil,ErrShortRouteKey
        }
    }
    return pbkdf2.Key([]byte(passphrase),[]byte(domainSalt),Iterations,32,sha256.New),nil
}
