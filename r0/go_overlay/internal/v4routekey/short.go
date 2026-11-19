// Package v4routekey implements one offline, versioned route-key derivation.
// It does not change TLS SessionID, admission, or any on-wire fields.
// Short human-chosen secrets remain guessable even when the output is 32 bytes.
package v4routekey

import (
    "crypto/sha256"
    "errors"
    "golang.org/x/crypto/pbkdf2"
)

const Iterations = 4096 // v2: mobile-friendly, one time only; never per lane.
const MinLength = 8
const MaxLength = 32
const Version = 2
const domainSalt = "WBD-V4-ROUTE-KEY-PBKDF2-SHA256-v2\x00"

var ErrShortRouteKey = errors.New("route-key requires 8..32 ASCII letters/digits, case-sensitive")

func validate(passphrase string) error {
    if len(passphrase) < MinLength || len(passphrase) > MaxLength { return ErrShortRouteKey }
    for i := 0; i < len(passphrase); i++ {
        ch := passphrase[i]
        if !((ch >= '0' && ch <= '9') || (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z')) {
            return ErrShortRouteKey
        }
    }
    return nil
}

// Derive is for initial enrollment or an explicitly changed key, not reconnect.
// v1 (240000 iterations) is intentionally NOT silently accepted as v2.
func Derive(passphrase string) ([]byte, error) {
    if err := validate(passphrase); err != nil { return nil, err }
    return pbkdf2.Key([]byte(passphrase), []byte(domainSalt), Iterations, 32, sha256.New), nil
}
