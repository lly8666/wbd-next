// TEST-ONLY ARM64 Bionic/NativeBridge gate. Not a WBD transport,
// not a FakeTCP peer, and never included in the production Root APK.
#include <dlfcn.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

int main(int argc, char **argv) {
    puts("WBD_ANDROID_ARM64_NDK_MIN_EXEC_STARTED");
    fflush(stdout);
    if (argc == 2 && strcmp(argv[1], "--self") == 0) {
        puts("WBD_ANDROID_ARM64_NDK_MIN_EXEC_PASS");
        return 0;
    }
    if (argc != 3 || (strcmp(argv[1], "--dlopen") != 0 &&
                      strcmp(argv[1], "--go-shared") != 0 &&
                      strcmp(argv[1], "--original-go-help") != 0 &&
                      strcmp(argv[1], "--mtu-budget") != 0)) {
        fputs("usage: probe --self | --dlopen /absolute/path/libwbd_engine.so | --go-shared /absolute/path/libgo.so | --original-go-help /absolute/path/liboriginal-go.so\n", stderr);
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
    if (strcmp(argv[1], "--mtu-budget") == 0) {
        // Exact production cold Rust C ABI; no invented owner or TLS state.
        // Compare with shared Rust default_1460_outer_ip... golden test.
        typedef struct {uint32_t version, size, outer, physical, peer,
                         record, ip, tcp, mode;} Input;
        typedef struct {uint32_t version, size, outer, syn, wire,
                         payload, inner, fragment;} Output;
        int (*budget)(const Input *,uint32_t,Output *,uint32_t) =
            (int (*)(const Input *,uint32_t,Output *,uint32_t))
                dlsym(h,"wbd_m0_v4_mtu_budget_v1");
        if (!budget) return 10;
        const uint32_t inner[4]={1389,1375,1373,1358};
        for (uint32_t mode=0;mode<4;mode++) {
            Input in={1,sizeof(Input),1460,1500,1420,0,20,20,mode};
            Output out={0};
            if(budget(&in,sizeof(in),&out,sizeof(out))!=0 ||
               out.version!=1 || out.size!=sizeof(out) ||
               out.outer!=1460 || out.syn!=1420 ||
               out.wire!=1420 || out.inner!=inner[mode]) return 11;
            printf("WBD_TRANSLATED_RUST_MTU mode=%u inner=%u\n",mode,out.inner);
        }
        puts("WBD_TRANSLATED_ARM64_RUST_MTU_BUDGET_PASS");
        return 0;
    }
    if (strcmp(argv[1], "--go-shared") == 0) {
        puts("WBD_ANDROID_ARM64_GO_CSHARED_DLOPEN_PASS");
        fflush(stdout);
        void *symbol = dlsym(h, "WBD_AndroidGoCSharedProbe");
        if (symbol == NULL) {
            fputs("WBD_ANDROID_ARM64_GO_CSHARED_SYMBOL_FAIL\n", stderr);
            return 6;
        }
        // This is a constant-return runtime probe, never WBD auth or
        // a fake transport. Distinguish dlopen Go runtime constructors
        // from the first exported Go function call.
        int (*go_probe)(void) = (int (*)(void))symbol;
        puts("WBD_ANDROID_ARM64_GO_CSHARED_CALL_ENTER");
        fflush(stdout);
        if (go_probe() != 2666) return 7;
        puts("WBD_ANDROID_ARM64_GO_CSHARED_CALL_PASS");
        return 0;
    }
    if (strcmp(argv[1], "--original-go-help") == 0) {
        // Call real ORIGINAL-Go v4productcli.Run("client", "--help")
        // through a test-only c-shared export, not a constant-return shim.
        // NativeBridge must actually load that .so together with the
        // original source-locked libwbd_engine.so, then enter Go runtime.
        void *symbol = dlsym(h, "WBD_AndroidRootOriginalGoHelp");
        if (symbol == NULL) {
            fprintf(stderr, "WBD_ANDROID_ARM64_ORIGINAL_GO_CSHARED_DLSYM_FAIL: %s\n", dlerror());
            return 8;
        }
        int (*real_help)(void) = (int (*)(void))symbol;
        puts("WBD_ANDROID_ARM64_ORIGINAL_GO_CSHARED_HELP_ENTER");
        fflush(stdout);
        int result = real_help();
        if (result != 0) {
            fprintf(stderr, "WBD_ANDROID_ARM64_ORIGINAL_GO_CSHARED_HELP_FAIL: %d\n", result);
            return 9;
        }
        puts("WBD_ANDROID_ARM64_ORIGINAL_GO_CSHARED_HELP_PASS");
        return 0;
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
