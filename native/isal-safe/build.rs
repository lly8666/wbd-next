// Target-aware, pinned ISA-L linkage. This script deliberately DOES NOT
// build a native library or silently replace a requested native backend.
// Scalar fallback belongs to the codec when Cargo feature "native" is absent.
// Target-specific archives/manifest and Actions entrypoints belong to M0.
use std::{env, fs, path::{Path, PathBuf}};

const PINNED_SOURCE: &str = "c387163fcbca62701d646149564c550c78a4f985";

fn archive(prefix: &Path, file: &str) -> Option<PathBuf> {
    for dir in ["lib", "lib64", ""] {
        let path = if dir.is_empty() { prefix.join(file) } else { prefix.join(dir).join(file) };
        if path.is_file() { return Some(path); }
    }
    None
}

fn main() {
    for var in ["WBD_ISAL_PREFIX", "WBD_ISAL_ARTIFACT_TARGET", "WBD_ISAL_SOURCE_SHA"] {
        println!("cargo:rerun-if-env-changed={var}");
    }
    let target = env::var("TARGET").expect("Cargo TARGET missing");
    let host = env::var("HOST").expect("Cargo HOST missing");
    println!("cargo:rerun-if-env-changed=CARGO_FEATURE_NATIVE");
    println!("cargo:rustc-env=WBD_ISAL_TARGET={target}");

    if env::var_os("CARGO_FEATURE_NATIVE").is_none() {
        println!("cargo:rustc-env=WBD_ISAL_BACKEND=native-disabled");
        println!("cargo:warning=ISA-L native feature off for {target}; safe wrapper reports Unavailable, codec must select scalar/XOR");
        return;
    }

    let (file, libname, family) = match target.as_str() {
        "x86_64-unknown-linux-gnu" => ("libisal.a", "isal", "linux-x64-dispatch"),
        "aarch64-unknown-linux-gnu" => ("libisal.a", "isal", "linux-arm64-neon-capable"),
        "x86_64-pc-windows-msvc" => ("isa-l_static.lib", "isa-l_static", "windows-x64-msvc"),
        _ => panic!("ISA-L native requested for unsupported TARGET {target}; omit feature native for scalar/XOR fallback; Windows GNU/MSVC and Linux archives are not interchangeable"),
    };
    let prefix = PathBuf::from(env::var_os("WBD_ISAL_PREFIX")
        .expect("native ISA-L requires pinned WBD_ISAL_PREFIX, no system-library fallback"));
    let lib = archive(&prefix,file).unwrap_or_else(|| panic!(
        "target {target} requires pinned STATIC {} under WBD_ISAL_PREFIX lib/, lib64/ or root (Windows: nmake isa-l_static.lib); omit feature native for scalar/XOR fallback",
        file));
    // A cross-compiled archive cannot be called native-tested. Requiring a
    // target witness makes accidental host-prefix re-use a detectable error.
    // Final architecture and symbol match is additionally checked by linker.
    if host != target {
        let witnessed = env::var("WBD_ISAL_ARTIFACT_TARGET")
            .expect("cross ISA-L requires WBD_ISAL_ARTIFACT_TARGET provenance");
        assert_eq!(witnessed,target,"cross ISA-L archive target mismatch");
        let source = env::var("WBD_ISAL_SOURCE_SHA")
            .expect("cross ISA-L requires WBD_ISAL_SOURCE_SHA provenance");
        assert_eq!(source,PINNED_SOURCE,"cross ISA-L source is not v2.31.1 pinned SOURCE");
    }
    if let Ok(source) = env::var("WBD_ISAL_SOURCE_SHA") {
        assert_eq!(source,PINNED_SOURCE,"ISA-L source identity mismatch");
    }
    let dir = lib.parent().expect("archive parent missing");
    // Check that archive is at least non-empty, never claim object architecture
    // or actual runtime instruction choice from this check alone.
    assert!(fs::metadata(&lib).expect("ISA-L metadata missing").len() > 0,
        "empty ISA-L archive");
    println!("cargo:rerun-if-changed={}",lib.display());
    println!("cargo:rustc-link-search=native={}",dir.display());
    println!("cargo:rustc-link-lib=static={libname}");
    println!("cargo:rustc-env=WBD_ISAL_BACKEND={family}");
    println!("cargo:rustc-env=WBD_ISAL_LIBRARY={file}");
    println!("cargo:warning=ISA-L static {file} linked for TARGET={target} HOST={host}; build/link success does not prove native runtime dispatch, NEON execution, real driver or product load");
}
