package v4routekey

import (
    "encoding/hex"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func TestH2207MobileFriendlyV2Vectors(t *testing.T) {
    if Iterations != 4096 || Version != 2 { t.Fatal("unexpected KDF version/cost") }
    for _, tc := range []struct { input, want string }{
        {"Abc12345", "b3745a18edd59a1ce6aa2586ae5d90c3ec2eee3fbfafa059783e4492e2bc0539"},
        {"A1b2C3d4E5f6G7h8", "68ef025a9224cafa38c55e4fad14eec0fece1642c8679a41368fee0f5702033e"},
        {"ABCdef0123456789ABCdef0123456789", "fcb0fd63fb6e807da50afc7d1c39a9df68b7c39ae67ed2cc2db76ebe9127054e"},
    } {
        got, err := Derive(tc.input)
        if err != nil || hex.EncodeToString(got) != tc.want { t.Fatalf("v2 vector %d %v", len(got), err) }
    }
}

func TestH2207RejectInvalidShortKey(t *testing.T) {
    for _, input := range []string{"", "1234567", strings.Repeat("x", 33), "ABC 12345", "ABC-12345", "ABC_12345", "ABC\n12345", "abcdefgh\x00", "中文密钥A1", "ＡＢＣ１２３４５"} {
        if got, err := Derive(input); err == nil || got != nil { t.Fatal("accepted invalid input") }
    }
    a, _ := Derive("Abc12345"); b, _ := Derive("abc12345")
    if hex.EncodeToString(a) == hex.EncodeToString(b) { t.Fatal("key lost case sensitivity") }
}

func TestH2208PersistentOncePerKeyAndFastRestarts(t *testing.T) {
    dir := t.TempDir()
    // testing.T.TempDir may be mode 0755 on Linux; an actual cache owner
    // MUST have private 0700. Make only the test fixture private, not the
    // production permission guard, before enrolling the first short key.
    if err := os.Chmod(dir, 0700); err != nil { t.Fatal(err) }
    path := filepath.Join(dir, "owned-route-key.json")
    first, hit, err := Resolve("Abc12345", path)
    if err != nil || hit || len(first) != 32 { t.Fatalf("initial derive: hit=%v err=%v", hit, err) }
    st, err := os.Stat(path)
    if err != nil { t.Fatal("cache file missing", err) }
    if st.Mode().IsRegular() == false { t.Fatal("cache must be regular") }
    second, hit, err := Resolve("Abc12345", path)
    if err != nil || !hit || !strings.EqualFold(hex.EncodeToString(first), hex.EncodeToString(second)) { t.Fatal("restart must use persisted 32B key") }
    rotated, hit, err := Resolve("Abc12346", path)
    if err != nil || hit || hex.EncodeToString(rotated) == hex.EncodeToString(first) { t.Fatal("changed short key must rotate persistent key") }
    _, hit, err = Resolve("Abc12346", path)
    if err != nil || !hit { t.Fatal("rotated key not reused") }
    if err := os.WriteFile(path, []byte("{bad"), 0600); err != nil { t.Fatal(err) }
    if _, _, err := Resolve("Abc12346", path); err == nil { t.Fatal("corrupt cache must fail closed") }
}
