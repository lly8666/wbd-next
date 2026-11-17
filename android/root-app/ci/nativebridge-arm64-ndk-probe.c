// TEST-ONLY ARM64 Bionic/NativeBridge gate. Not a WBD transport,
// not a FakeTCP peer, and never included in the production Root APK.
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    puts("WBD_ANDROID_ARM64_NDK_MIN_EXEC_STARTED");
    fflush(stdout);
    if (argc == 2 && strcmp(argv[1], "--self") == 0) {
        puts("WBD_ANDROID_ARM64_NDK_MIN_EXEC_PASS");
        return 0;
    }
    if (argc != 3 || strcmp(argv[1], "--dlopen") != 0) {
        fputs("usage: probe --self | --dlopen /absolute/path/libwbd_engine.so\n", stderr);
        return 2;
    }
    // Real source-locked Rust shared ELF, no fake ABI and no native WBD
    // function invocation. Tests Bionic translation/load/constructors only.
    if (argv[2][0] != '/') return 3;
    puts("WBD_ANDROID_ARM64_RUST_DLOPEN_ENTER");
    fflush(stdout);
    void *h = dlopen(argv[2], RTLD_NOW | RTLD_LOCAL);
    if (h == NULL) {
        fprintf(stderr, "WBD_ANDROID_ARM64_RUST_DLOPEN_FAIL: %s\n", dlerror());
        return 4;
    }
    // Do not call an owner symbol with fabricated credentials or packets.
    void *sym = dlsym(h, "wbd_m0_embedded_go_prepare_client");
    if (sym == NULL) {
        fputs("WBD_ANDROID_ARM64_RUST_DLSYM_FAIL\n", stderr);
        return 5;
    }
    puts("WBD_ANDROID_ARM64_RUST_DLOPEN_PASS");
    // Allow process exit to own cleanup (avoid a synthetic Stop call).
    return 0;
}
